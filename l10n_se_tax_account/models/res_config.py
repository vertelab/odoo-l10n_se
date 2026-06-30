# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # --- Skatteverket API: Tax Account settings ---
    skv_test_mode = fields.Boolean(
        string='Skatteverket Test Mode',
        related='company_id.skv_test_mode',
        readonly=False,
        help="Use Skatteverket's test environment instead of production.")

    skv_auth_method = fields.Selection(
        selection=[('cert', 'Certificate'), ('e_id', 'E-identification')],
        string='SKV Auth Method',
        related='company_id.skv_auth_method',
        readonly=False,
        help="Authentication method for Skatteverket API.")

    skv_api_url = fields.Char(
        string='SKV Tax Account API URL',
        related='company_id.skv_api_url',
        readonly=False,
        help="Skatteverket API endpoint for tax account transactions.")

    skv_auth_url = fields.Char(
        string='SKV Auth URL',
        related='company_id.skv_auth_url',
        readonly=False,
        help="Skatteverket OAuth2 authorization endpoint.")

    skv_token_url = fields.Char(
        string='SKV Token URL',
        related='company_id.skv_token_url',
        readonly=False,
        help="Skatteverket OAuth2 token endpoint.")

    skv_match_tolerance_days = fields.Integer(
        string='Match Tolerance (Days)',
        related='company_id.skv_match_tolerance_days',
        readonly=False,
        help="Number of days difference allowed when auto-matching "
             "tax account transactions with booked entries.")
