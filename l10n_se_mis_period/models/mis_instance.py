from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError, ValidationError
from collections import defaultdict

import base64
from lxml import etree

from odoo.addons.l10n_se_mis_period.models.expression_evaluator import ExpressionEvaluatorExtended
from odoo.addons.l10n_se_mis_period.models.aep import AccountingExpressionProcessorExtended as AEPE

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
        elif self.analytic_plan_id:
            domain.extend([("analytic_account_id.plan_id", "=", self.analytic_plan_id.id)])
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
        expression_evaluator = ExpressionEvaluatorExtended(
            aep,
            period.date_from,
            period.date_to,
            None,  # target_move now part of additional_move_line_filter
            period.source_aml_model_name,
            period._get_additional_move_line_filter(),
        )
        #
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

            if self.report_id.account_model == 'account.account':
                domain = aep.get_aml_domain_for_expr(
                    expr,
                    period.date_from,
                    period.date_to,
                    None,  # target_move now part of additional_move_line_filter
                    account_id,
                    find_moves_by_period=self.find_moves_by_period,  # ADDED
                    accounting_method=self.accounting_method,  # ADDED
                )
            else:
                domain = aep.get_generic_aml_domain_for_expr(
                    expr,
                    period.date_from,
                    period.date_to,
                    None,  # target_move now part of additional_move_line_filter
                    account_id,
                    find_moves_by_period=self.find_moves_by_period,  # ADDED
                    accounting_method=self.accounting_method,  # ADDED
                    report_id=self.report_id
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


class MisReportInstanceFixAnalyticTag(models.Model):  # Should Be Called MisReportInstance
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
        analytic_plan_id = filters.get("analytic_account_id.plan_id", {}).get("value")
        if analytic_plan_id:
            analytic_group = self.env["account.analytic.plan"].browse(
                analytic_plan_id
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
            filter_descriptions.append(
                _("Analytic Tags: %s")
                % ", ".join([rec for rec in analytic_tag_names])
            )
        return filter_descriptions

    def _add_analytic_filters_to_context(self, context):
        self.ensure_one()
        if self.analytic_account_id:
            context["mis_report_filters"]["analytic_account_id"] = {
                "value": self.analytic_account_id.id,
                "operator": "=",
            }
        if self.analytic_plan_id:
            context["mis_report_filters"]["analytic_account_id.plan_id"] = {
                "value": self.analytic_plan_id.id,
                "operator": "=",
            }
        if self.analytic_tag_ids:
            context["mis_report_filters"]["analytic_tag_ids"] = {
                "value": self.analytic_tag_ids.ids,
                "operator": "all",
            }
