# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

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
