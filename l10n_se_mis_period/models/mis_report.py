from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict

import base64
from lxml import etree

from odoo.addons.l10n_se_mis_period.models.expression_evaluator import ExpressionEvaluatorExtended
from odoo.addons.l10n_se_mis_period.models.aep import AccountingExpressionProcessorExtended as AEP
from odoo.addons.l10n_se_mis_period.models.kpimatrix import KpiMatrixExtended as KME

from .simple_array import SimpleArray, named_simple_array

from odoo.addons.mis_builder.models.accounting_none import AccountingNone
from odoo.addons.mis_builder.models.mis_report import SubKPITupleLengthError, SubKPIUnknownTypeError, TYPE_STR
from odoo.addons.mis_builder.models.mis_safe_eval import DataError


class AutoStruct(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class MisReport(models.Model):
    _inherit = 'mis.report'

    use_currency_suffix = fields.Boolean("Currency Suffix",
                                         help="Use currency set on mis report or the company currency as a suffix.")

    mis_field = fields.Char(string='Target Field')

    @api.model
    def _get_target_move_domain(self, target_move, aml_model_name):
        """
        Obtain a domain to apply on a move-line-like model, to get posted
        entries or return all of them (always excluding cancelled entries).

        :param: target_move: all|posted
        :param: aml_model_name: an optional move-line-like model name
                (defaults to account.move.line)
        """
        if not self._supports_target_move_filter(aml_model_name):
            return []

        if target_move == "posted":
            return [("parent_state", "=", "posted")]
        if target_move == "draft":
            return [("parent_state", "=", "draft")]
        elif target_move == "all":
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
                print("kpi_matrix", kpi_matrix)
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
        aep = AEP(companies, currency, self.account_model)
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

    @api.depends('move_lines_source')
    def _compute_account_model(self):
        for record in self:
            if record.move_lines_source.model == 'mis.budget.by.analytic.account.item':
                record.account_model = (
                    record.move_lines_source.sudo()
                    .field_id.filtered(lambda r: r.name == "analytic_account_id")
                    .relation
                )
            else:
                record.account_model = (
                    record.move_lines_source.sudo()
                    .field_id.filtered(lambda r: r.name == "account_id")
                    .relation
                )
