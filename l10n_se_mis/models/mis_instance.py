from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError
from collections import defaultdict

import base64
from lxml import etree
from .aep import AccountingExpressionProcessorExtended as AEPE
from .expression_evaluator import ExpressionEvaluatorExtended as EEE
from .kpimatrix import KpiMatrixExtended as KME
from .simple_array import SimpleArray, named_simple_array
from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.mis_report import SubKPITupleLengthError, SubKPIUnknownTypeError, TYPE_STR
from odoo.addons.mis_builder.models.mis_safe_eval import DataError

# ~ from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

SRC_ACTUALS = "actuals"
SRC_ACTUALS_ALT = "actuals_alt"
SRC_CMPCOL = "cmpcol"
SRC_SUMCOL = "sumcol"

MODE_NONE = "none"
MODE_FIX = "fix"
MODE_REL = "relative"


class AutoStruct(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MisReportInstancePeriod(models.Model):
    _inherit = 'mis.report.instance.period'

    hide_opening_closing_period = fields.Boolean(string="Hide Opening/Closing Period")

    def _get_additional_move_line_filter(self):
        domain = super(MisReportInstancePeriod, self)._get_additional_move_line_filter()
        if (
                self.source_aml_model_name == "account.move.line"
                and self.report_instance_id.target_move == "draft"
        ):
            domain.extend([("move_id.state", "=", "draft")])
        if (self.source_aml_model_name == "account.move.line") and self.report_instance_id.hide_opening_closing_period:
            domain.extend([("move_id.period_id.special", "=", False)])
        elif (self.source_aml_model_name == "account.move.line") and self.hide_opening_closing_period:
            domain.extend([("move_id.period_id.special", "=", False)])
        return domain

    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Analytic Account"
    )
    analytic_plan_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        string="Analytic Account Plan",
    )


class MisReportInstance(models.Model):
    _inherit = 'mis.report.instance'

    find_moves_by_period = fields.Boolean(
        default=False, string="Find Move Based On Period",
        help="A little confusing but vouchers/invoices has dates and which period they belong to. By default the mis "
             "report finds moves based on date. If this is checked then we find them based on period",
        # ~ states={'posted':[('readonly',True)]}
    )
    hide_lines_that_are_empty = fields.Boolean(default=False, string="Hide empty lines")

    accounting_method = fields.Selection(selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden'), ],
                                         default='invoice', string='Redovisningsmetod',
                                         help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden "
                                              "skall välja fakturametoden i sista perioden/bokslutsperioden")
    target_move = fields.Selection(selection_add=[('draft', 'All Unposted Entries')], ondelete={"draft": "set default"})
    hide_opening_closing_period = fields.Boolean(string="Hide Opening/Closing Period")
    analytic_account_id = fields.Many2one(
        comodel_name="account.analytic.account", string="Analytic Account"
    )
    analytic_plan_id = fields.Many2one(
        comodel_name="account.analytic.plan",
        string="Analytic Account Plan",
    )

    # ~ def _compute_matrix(self):
    # ~ """Compute a report and return a KpiMatrix.

    # ~ The key attribute of the matrix columns (KpiMatrixCol)
    # ~ is guaranteed to be the id of the mis.report.instance.period.
    # ~ """
    # ~ self.ensure_one()
    # ~ aep = self.report_id._prepare_aep(self.query_company_ids, self.currency_id)
    # ~ kpi_matrix = self.report_id.prepare_kpi_matrix(self.multi_company)
    # ~ for period in self.period_ids:
    # ~ description = None
    # ~ if period.mode == MODE_NONE:
    # ~ pass
    # ~ elif not self.display_columns_description:
    # ~ pass
    # ~ elif period.date_from == period.date_to and period.date_from:
    # ~ description = self._format_date(period.date_from)
    # ~ elif period.date_from and period.date_to:
    # ~ date_from = self._format_date(period.date_from)
    # ~ date_to = self._format_date(period.date_to)
    # ~ description = _("from %s to %s") % (date_from, date_to)
    # ~ self._add_column(aep, kpi_matrix, period, period.name, description)
    # ~ kpi_matrix.compute_comparisons()
    # ~ kpi_matrix.compute_sums(self.currency_id)
    # ~ return kpi_matrix

    def compute(self):
        self.ensure_one()
        kpi_matrix = self._compute_matrix()
        return kpi_matrix.as_dict(self.hide_lines_that_are_empty)

    def _add_column_move_lines(self, aep, kpi_matrix, period, label, description):
        if not period.date_from or not period.date_to:
            raise UserError(
                _("Column %s with move lines source must have from/to dates.")
                % (period.name,)
            )
        expression_evaluator = EEE(
            aep,
            period.date_from,
            period.date_to,
            None,  # target_move now part of additional_move_line_filter
            period._get_additional_move_line_filter(),
            period.source_aml_model_name,
        )

        expression_evaluator.find_moves_by_period = self.find_moves_by_period  # GO BY PERIOD
        expression_evaluator.accounting_method = self.accounting_method
        self.report_id._declare_and_compute_period_currency(
            expression_evaluator,
            kpi_matrix,
            period.id,
            label,
            description,
            self.currency_id,
            period.subkpi_ids,
            period._get_additional_query_filter,
            no_auto_expand_accounts=self.no_auto_expand_accounts,
        )

    def drilldown(self, arg):
        self.ensure_one()
        period_id = arg.get("period_id")
        expr = arg.get("expr")
        account_id = arg.get("account_id")
        if period_id and expr and AEPE.has_account_var(expr):
            period = self.env["mis.report.instance.period"].browse(period_id)
            aep = AEPE(
                self.query_company_ids, self.currency_id, self.report_id.account_model
            )
            aep.parse_expr(expr)
            aep.done_parsing()
            domain = aep.get_aml_domain_for_expr(
                expr,
                period.date_from,
                period.date_to,
                None,  # target_move now part of additional_move_line_filter
                account_id,
                find_moves_by_period=self.find_moves_by_period,  # ADDED
                accounting_method=self.accounting_method,  # ADDED
            )
            domain.extend(period._get_additional_move_line_filter())
            return {
                "name": self._get_drilldown_action_name(arg),
                "domain": domain,
                "type": "ir.actions.act_window",
                "res_model": period.source_aml_model_name,
                "views": [[False, "list"], [False, "form"]],
                "view_mode": "list",
                "target": "current",
                "context": {"active_test": False},
            }
        else:
            return False


class MisReport(models.Model):  ### Should Be Called MisReport
    _inherit = 'mis.report'

    use_currency_suffix = fields.Boolean("Currency Suffix",
                                         help="Use currency set on mis report or the company currency as a suffix.")

    @api.model
    def _get_target_move_domain(self, target_move, aml_model_name):
        """
        Obtain a domain to apply on a move-line-like model, to get posted
        entries or return all of them (always excluding cancelled entries).

        :param: target_move: all|posted
        :param: aml_model_name: an optional move-line-like model name
                (defaults to accaount.move.line)
        """
        if not self._supports_target_move_filter(aml_model_name):
            return []

        if target_move == "posted":
            return [("parent_state", "=", "posted")]
        if target_move == "draft":
            return [("parent_state", "=", "draft")]
        elif target_move == "all":
            # all (in Odoo 13+, there is also the cancel state that we must ignore)
            return [("parent_state", "in", ("posted", "draft"))]
        else:
            raise UserError(_("Unexpected value %s for target_move.") % (target_move,))

    def _declare_and_compute_period_currency(
            self,
            expression_evaluator,
            kpi_matrix,
            col_key,
            col_label,
            col_description,
            currency_id,
            subkpis_filter=None,
            get_additional_query_filter=None,
            locals_dict=None,
            no_auto_expand_accounts=False,
    ):
        """Evaluate a report for a given period, populating a KpiMatrix.

        :param expression_evaluator: an ExpressionEvaluator instance
        :param kpi_matrix: the KpiMatrix object to be populated created
                           with prepare_kpi_matrix()
        :param col_key: the period key to use when populating the KpiMatrix
        :param subkpis_filter: a list of subkpis to include in the evaluation
                               (if empty, use all subkpis)
        :param get_additional_query_filter: a bound method that takes a single
                                            query argument and returns a
                                            domain compatible with the query
                                            underlying model
        :param locals_dict: personalized locals dictionary used as evaluation
                            context for the KPI expressions
        :param no_auto_expand_accounts: disable expansion of account details
        """
        self.ensure_one()

        # prepare the localsdict
        if locals_dict is None:
            locals_dict = {}

        # Evaluate subreports
        for subreport in self.subreport_ids:
            subreport_locals_dict = subreport.subreport_id._evaluate(
                expression_evaluator, subkpis_filter, get_additional_query_filter
            )
            locals_dict[subreport.name] = AutoStruct(
                **{
                    srk.name: subreport_locals_dict.get(srk.name, AccountingNone)
                    for srk in subreport.subreport_id.kpi_ids
                }
            )

        locals_dict.update(self.prepare_locals_dict())
        locals_dict["date_from"] = fields.Date.from_string(
            expression_evaluator.date_from
        )
        locals_dict["date_to"] = fields.Date.from_string(expression_evaluator.date_to)

        # fetch non-accounting queries
        locals_dict.update(
            self._fetch_queries(
                expression_evaluator.date_from,
                expression_evaluator.date_to,
                get_additional_query_filter,
            )
        )

        # use AEP to do the accounting queries
        expression_evaluator.aep_do_queries()

        self._declare_and_compute_col_currency(
            expression_evaluator,
            kpi_matrix,
            col_key,
            col_label,
            col_description,
            subkpis_filter,
            locals_dict,
            currency_id,
            self.use_currency_suffix,
            no_auto_expand_accounts,
        )

    def _declare_and_compute_col_currency(  # noqa: C901 (TODO simplify this fnction)
            self,
            expression_evaluator,
            kpi_matrix,
            col_key,
            col_label,
            col_description,
            subkpis_filter,
            locals_dict,
            currency_id,
            use_currency_suffix,
            no_auto_expand_accounts=False,
    ):
        """This is the main computation loop.

        It evaluates the kpis and puts the results in the KpiMatrix.
        Evaluation is done through the expression_evaluator so data sources
        can provide their own mean of obtaining the data (eg preset
        kpi values for budget, or alternative move line sources).
        """

        if subkpis_filter:
            # TODO filter by subkpi names
            subkpis = [subkpi for subkpi in self.subkpi_ids if subkpi in subkpis_filter]
        else:
            subkpis = self.subkpi_ids

        SimpleArray_cls = named_simple_array(
            "SimpleArray_{}".format(col_key), [subkpi.name for subkpi in subkpis]
        )
        locals_dict["SimpleArray"] = SimpleArray_cls

        col = kpi_matrix.declare_col(
            col_key, col_label, col_description, locals_dict, subkpis
        )

        compute_queue = self.kpi_ids
        recompute_queue = []
        while True:
            for kpi in compute_queue:
                # build the list of expressions for this kpi
                expressions = kpi._get_expressions(subkpis)

                (
                    vals,
                    drilldown_args,
                    name_error,
                ) = expression_evaluator.eval_expressions(expressions, locals_dict)
                for drilldown_arg in drilldown_args:
                    if not drilldown_arg:
                        continue
                    drilldown_arg["period_id"] = col_key
                    drilldown_arg["kpi_id"] = kpi.id

                if name_error:
                    recompute_queue.append(kpi)
                else:
                    # no error, set it in locals_dict so it can be used
                    # in computing other kpis
                    if not subkpis or not kpi.multi:
                        locals_dict[kpi.name] = vals[0]
                    else:
                        locals_dict[kpi.name] = SimpleArray_cls(vals)

                # even in case of name error we set the result in the matrix
                # so the name error will be displayed if it cannot be
                # resolved by recomputing later

                if subkpis and not kpi.multi:
                    # here we have one expression for this kpi, but
                    # multiple subkpis (so this kpi is most probably
                    # a sum or other operation on multi-valued kpis)
                    if isinstance(vals[0], tuple):
                        vals = vals[0]
                        if len(vals) != col.colspan:
                            raise SubKPITupleLengthError(
                                _(
                                    'KPI "{}" is valued as a tuple of '
                                    "length {} while a tuple of length {} "
                                    "is expected."
                                ).format(kpi.description, len(vals), col.colspan)
                            )
                    elif isinstance(vals[0], DataError):
                        vals = (vals[0],) * col.colspan
                    else:
                        raise SubKPIUnknownTypeError(
                            _(
                                'KPI "{}" has type {} while a tuple was '
                                "expected.\n\nThis can be fixed by either:\n\t- "
                                "Changing the KPI value to a tuple of length "
                                "{}\nor\n\t- Changing the "
                                "KPI to `multi` mode and giving an explicit "
                                "value for each sub-KPI."
                            ).format(kpi.description, type(vals[0]), col.colspan)
                        )
                if len(drilldown_args) != col.colspan:
                    drilldown_args = [None] * col.colspan

                ####
                kpi_matrix.set_values_currency(kpi, col_key, vals, drilldown_args, currency_id=currency_id,
                                      use_currency_suffix=use_currency_suffix)

                if (
                        name_error
                        or no_auto_expand_accounts
                        or not kpi.auto_expand_accounts
                ):
                    continue

                for (
                        account_id,
                        vals,
                        drilldown_args,
                        _name_error,
                ) in expression_evaluator.eval_expressions_by_account(
                    expressions, locals_dict
                ):
                    for drilldown_arg in drilldown_args:
                        if not drilldown_arg:
                            continue
                        drilldown_arg["period_id"] = col_key
                        drilldown_arg["kpi_id"] = kpi.id
                        # currency_id5
                    kpi_matrix.set_values_detail_account_currency(
                        kpi, col_key, account_id, vals, drilldown_args, currency_id=currency_id,
                        use_currency_suffix=use_currency_suffix
                    )

            if len(recompute_queue) == 0:
                # nothing to recompute, we are done
                break
            if len(recompute_queue) == len(compute_queue):
                # could not compute anything in this iteration
                # (ie real Name errors or cyclic dependency)
                # so we stop trying
                break
            # try again
            compute_queue = recompute_queue
            recompute_queue = []

    def _prepare_aep(self, companies, currency=None):
        self.ensure_one()
        aep = AEPE(companies, currency, self.account_model)
        for kpi in self.all_kpi_ids:
            for expression in kpi.expression_ids:
                if expression.name:
                    aep.parse_expr(expression.name)
        aep.done_parsing()
        return aep

    def prepare_kpi_matrix(self, multi_company=False):
        self.ensure_one()
        kpi_matrix = KME(self.env, multi_company, self.account_model)
        for kpi in self.kpi_ids:
            kpi_matrix.declare_kpi(kpi)
        return kpi_matrix

    def get_kpis_by_account_id(self, company):
        """ Return { account_id: set(kpi) } """
        aep = self._prepare_aep(company)
        res = defaultdict(set)
        for kpi in self.kpi_ids:
            for expression in kpi.expression_ids:
                if not expression.name:
                    continue
                account_ids = aep.get_account_ids_for_expr(expression.name)
                for account_id in account_ids:
                    res[account_id].add(kpi)
        return res


class MisReportInstanceFixAnalyticTag(models.Model):  ### Should Be Called MisReportInstance
    _inherit = "mis.report.instance"

    @api.model
    def get_filter_descriptions_from_context(self):
        filters = self.env.context.get("mis_report_filters", {})
        analytic_account_id = filters.get("analytic_account_id", {}).get("value")
        filter_descriptions = []
        if analytic_account_id:
            analytic_account = self.env["account.analytic.account"].browse(
                analytic_account_id
            )
            filter_descriptions.append(
                _("Analytic Account: %s") % analytic_account.display_name
            )
        analytic_group_id = filters.get("analytic_account_id.group_id", {}).get("value")
        if analytic_group_id:
            analytic_group = self.env["account.analytic.group"].browse(
                analytic_group_id
            )
            filter_descriptions.append(
                _("Analytic Account Group: %s") % analytic_group.display_name
            )
        analytic_tag_value = filters.get("analytic_tag_ids", {}).get("value")
        if analytic_tag_value:
            # TODO 14 
            analytic_tag_names = []
            for tag in analytic_tag_value:
                tag_record = self.env['account.analytic.tag'].browse(tag)
                if tag_record:
                    for account_analytic_distribution in tag_record.analytic_distribution_ids:
                        account_analytic_distribution.account_id.name
                        analytic_tag_names.append(account_analytic_distribution.account_id.name)
            # ~ analytic_tag_names = self.resolve_2many_commands(
            # ~ "analytic_tag_ids", analytic_tag_value, ["name"]
            # ~ )
            filter_descriptions.append(
                _("Analytic Tags: %s")
                % ", ".join([rec for rec in analytic_tag_names])
            )
        return filter_descriptions
