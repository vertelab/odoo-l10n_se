from odoo import fields, api, models, _
import logging
_logger = logging.getLogger(__name__)


class Company(models.Model):
    _inherit = 'res.company'
    ag_contact = fields.Many2many(comodel_name='res.partner',
        string='Arbetsgivare kontaktperson',
        domain=[('is_company', '=', False)])
    agd_journal = fields.Many2one(comodel_name='account.journal',
        string='Arbetsgivardeklaration journal')
    accounting_method = fields.Selection(
        selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden')],
        string='Redovisningsmetod',
        help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden "
             "skall välja fakturametoden i sista perioden/bokslutsperioden")
    vat_declaration_frequency = fields.Selection(
        selection=[('month', 'Month'), ('quarter', 'Quarter'), ('year', 'Year')],
        string='Tax Declaration Frequency',
        help="Length of the VAT declaration period.")
    vat_report_template_id = fields.Many2one(
        'mis.report',
        string='VAT Report Template',
        default=lambda self: self.env.ref('l10n_se_mis.report_md').id,
        help="MIS report template used for VAT declarations.")
    pc_report_template_id = fields.Many2one(
        'mis.report',
        string='Periodic Compilation Report Template',
        default=lambda self: self.env.ref('l10n_se_mis.report_pc').id,
        help="MIS report template used for Periodic Compilation (EU sales list).")

    # --- Skatteverket API: Employer Declaration endpoint ---
    skv_agd_api_url = fields.Char(
        string='SKV AGD API URL',
        compute='_compute_skv_agd_api_url',
        store=True,
        readonly=False,
        help="Skatteverket API endpoint for employer declarations (AGD). "
             "Auto-populated based on test mode; override to customize.")

    @api.depends('skv_test_mode')
    def _compute_skv_agd_api_url(self):
        """Set default endpoint based on test/live mode when field is empty."""
        for company in self:
            if not company.skv_agd_api_url:
                if company.skv_test_mode:
                    company.skv_agd_api_url = 'https://test.api.skatteverket.se/arbetsgivare/v2/deklaration'
                else:
                    company.skv_agd_api_url = 'https://api.skatteverket.se/arbetsgivare/v2/deklaration'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vat_declaration_frequency = fields.Selection(
        selection=[('month', 'Month'), ('quarter', 'Quarter'), ('year', 'Year')],
        string='Tax Declaration Frequency',
        help="Length of the VAT declaration period.",
        related='company_id.vat_declaration_frequency',
        readonly=False)

    accounting_method = fields.Selection(
        selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden')],
        string='Redovisningsmetod',
        help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden "
             "skall välja fakturametoden i sista perioden/bokslutsperioden",
        related='company_id.accounting_method',
        readonly=False)

    vat_report_template_id = fields.Many2one(
        'mis.report',
        string='VAT Report Template',
        help="MIS report template used for VAT declarations.",
        related='company_id.vat_report_template_id',
        readonly=False)

    pc_report_template_id = fields.Many2one(
        'mis.report',
        string='Periodic Compilation Report Template',
        help="MIS report template used for Periodic Compilation (EU sales list).",
        related='company_id.pc_report_template_id',
        readonly=False)

    skv_agd_api_url = fields.Char(
        string='SKV AGD API URL',
        related='company_id.skv_agd_api_url',
        readonly=False,
        help="Skatteverket API endpoint for employer declarations (AGD).")
