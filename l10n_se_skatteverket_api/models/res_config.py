# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    skv_test_mode = fields.Boolean(
        string='Skatteverket Test Mode',
        related='company_id.skv_test_mode', readonly=False)

    skv_auth_method = fields.Selection(
        string='SKV Auth Method',
        related='company_id.skv_auth_method', readonly=False)

    skv_certificate = fields.Binary(
        string='Certificate (PEM)',
        related='company_id.skv_certificate', readonly=False)

    skv_certificate_pin = fields.Char(
        string='Certificate PIN',
        related='company_id.skv_certificate_pin', readonly=False)

    skv_auth_url = fields.Char(
        string='SKV Auth URL',
        related='company_id.skv_auth_url', readonly=False)

    skv_token_url = fields.Char(
        string='SKV Token URL',
        related='company_id.skv_token_url', readonly=False)

    skv_api_base_url = fields.Char(
        string='SKV API Base URL',
        related='company_id.skv_api_base_url', readonly=False)

    skv_oauth_client_id = fields.Char(
        string='SKV OAuth Client ID',
        related='company_id.skv_oauth_client_id', readonly=False)

    skv_oauth_secret = fields.Char(
        string='SKV OAuth Client Secret',
        related='company_id.skv_oauth_secret', readonly=False)
