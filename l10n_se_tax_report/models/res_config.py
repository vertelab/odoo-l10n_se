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
        'account.report',
        string='VAT Report Template',
        default=lambda self: self.env['account.report'].search(
            [('country_id.code', '=', 'SE'), ('name', '=', 'skatterapport')],
            limit=1).id,
        help="The account.report used for VAT declarations. Defaults to the "
             "Swedish tax report shipped by l10n_se.")
    pc_report_template_id = fields.Many2one(
        'account.report',
        string='Periodic Compilation Report Template',
        default=lambda self: self.env['account.report'].search(
            [('country_id.code', '=', 'SE'),
             ('name', '=', 'Periodisk sammanställning')], limit=1).id,
        help="The account.report used for Periodic Compilation (EU sales list).")

    # All SKV API fields moved to l10n_se_skatteverket_api/models/res_company.py


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vat_declaration_frequency = fields.Selection(
        string='Tax Declaration Frequency',
        help="Length of the VAT declaration period.",
        related='company_id.vat_declaration_frequency',
        readonly=False)

    accounting_method = fields.Selection(
        string='Redovisningsmetod',
        help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden "
             "skall välja fakturametoden i sista perioden/bokslutsperioden",
        related='company_id.accounting_method',
        readonly=False)

    vat_report_template_id = fields.Many2one(
        'account.report',
        string='VAT Report Template',
        help="Report used for VAT declarations.",
        related='company_id.vat_report_template_id',
        readonly=False)

    pc_report_template_id = fields.Many2one(
        'account.report',
        string='Periodic Compilation Report Template',
        help="Report used for Periodic Compilation (EU sales list).",
        related='company_id.pc_report_template_id',
        readonly=False)
