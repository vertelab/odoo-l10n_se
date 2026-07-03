from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    skv_test_mode = fields.Boolean(
        string='Skatteverket Test Mode',
        related='company_id.skv_test_mode',
        readonly=False)

    skv_auth_method = fields.Selection(
        selection=[('cert', 'Certificate'), ('e_id', 'E-identification')],
        string='SKV Auth Method',
        related='company_id.skv_auth_method',
        readonly=False)

    skv_auth_url = fields.Char(
        string='SKV Auth URL',
        related='company_id.skv_auth_url',
        readonly=False)

    skv_token_url = fields.Char(
        string='SKV Token URL',
        related='company_id.skv_token_url',
        readonly=False)

    skv_moms_api_url = fields.Char(
        string='SKV Moms API URL',
        related='company_id.skv_moms_api_url',
        readonly=False)

    skv_pc_api_url = fields.Char(
        string='SKV PC API URL',
        related='company_id.skv_pc_api_url',
        readonly=False)

    skv_skattekonto_api_url = fields.Char(
        string='SKV Tax Account API URL',
        related='company_id.skv_skattekonto_api_url',
        readonly=False)
