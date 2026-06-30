# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    skv_agi_api_url = fields.Char(
        string='SKV AGI API URL',
        default='https://api.skatteverket.se/arbetsgivare/v2/deklaration/individuppgift',
        help='URL for Skatteverket AGI (individuppgifter) API.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    skv_agi_api_url = fields.Char(
        related='company_id.skv_agi_api_url',
        readonly=False,
    )
