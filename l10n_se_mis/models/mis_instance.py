from openerp import models, fields, api,_
import logging
import base64
from lxml import etree
from .aep import AccountingExpressionProcessorExtended as AEPE
from .expression_evaluator import ExpressionEvaluatorExtended as EEE
from .kpimatrix import KpiMatrixExtended as KME
# ~ from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

class MisReportInstancePeriod(models.Model):
    _inherit = 'mis.report.instance.period'
    
    def _get_additional_move_line_filter(self):
        domain = super(MisReportInstancePeriod,self)._get_additional_move_line_filter()
        # ~ _logger.warning(f"additional domain: {domain}")
        if (
            self._get_aml_model_name() == "account.move.line"
            and self.report_instance_id.target_move == "draft"
        ):
            domain.extend([("move_id.state", "=", "draft")])
        return domain

class MisReportInstance(models.Model):
    _inherit = 'mis.report.instance'
    
    find_moves_by_period = fields.Boolean(
        default=False,string="Find Move Based On Period",
        help="A little confusing but vouchers/invoices has dates and which period they belong to. By default the mis report finds moves based on date. If this is checked then we find them based on period",
        # ~ states={'posted':[('readonly',True)]}
    )
    hide_lines_that_are_empty = fields.Boolean(default=False,string="Hide empty lines")
    
    accounting_method = fields.Selection(selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden'),], default='invoice',string='Redovisningsmetod',help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden skall välja fakturametoden i sista perioden/bokslutsperioden")
    target_move = fields.Selection(selection_add=[('draft', 'All Unposted Entries')], ondelete={"draft": "set default"})
    
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
            period._get_aml_model_name(),
        )
        # ~ look here
        expression_evaluator.find_moves_by_period = self.find_moves_by_period #GO BY PERIOD
        expression_evaluator.accounting_method = self.accounting_method
        self.report_id._declare_and_compute_period(
            expression_evaluator,
            kpi_matrix,
            period.id,
            label,
            description,
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
                    find_moves_by_period = self.find_moves_by_period, #ADDED
                    accounting_method = self.accounting_method, #ADDED
                )
                # ~ _logger.warning(f"drilldown {domain}")
                domain.extend(period._get_additional_move_line_filter())
                return {
                    "name": self._get_drilldown_action_name(arg),
                    "domain": domain,
                    "type": "ir.actions.act_window",
                    "res_model": period._get_aml_model_name(),
                    "views": [[False, "list"], [False, "form"]],
                    "view_mode": "list",
                    "target": "current",
                    "context": {"active_test": False},
                }
            else:
                return False
                

class MisReportInstance(models.Model): ### Should Be Called MisReport
    _inherit = 'mis.report'

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
        _logger.warning("JAKMAR OVERRIDE PREPARE_KPI_MATRIX METHOD")
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
        
        
class MisReportInstanceFixAnalyticTag(models.Model): ### Should Be Called MisReportInstance
    _inherit = "mis.report.instance"


    @api.model
    def get_filter_descriptions_from_context(self):
        _logger.warning("get_filter_descriptions_from_context")
        _logger.warning("get_filter_descriptions_from_context")
        _logger.warning("get_filter_descriptions_from_context")
        _logger.warning("get_filter_descriptions_from_context")
        _logger.warning("get_filter_descriptions_from_context")
        _logger.warning("get_filter_descriptions_from_context")
        _logger.warning("get_filter_descriptions_from_context")
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
            _logger.warning(f"{analytic_tag_value=}")
            # TODO 14 
            analytic_tag_names = []
            for tag in analytic_tag_value:
                tag_record = self.env['account.analytic.tag'].browse(tag)
                _logger.warning(f"{tag_record=}")
                if tag_record: 
                    for account_analytic_distribution in tag_record.analytic_distribution_ids:
                        _logger.warning(f"analytic account name = {account_analytic_distribution.account_id.name}")
                        account_analytic_distribution.account_id.name
                        analytic_tag_names.append(account_analytic_distribution.account_id.name)
            # ~ analytic_tag_names = self.resolve_2many_commands(
                # ~ "analytic_tag_ids", analytic_tag_value, ["name"]
            # ~ )
            _logger.warning(f"{analytic_tag_names=}")
            filter_descriptions.append(
                _("Analytic Tags: %s")
                % ", ".join([rec for rec in analytic_tag_names])
            )
        return filter_descriptions


