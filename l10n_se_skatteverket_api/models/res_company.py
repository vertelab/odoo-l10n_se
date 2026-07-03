# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # --- Skatteverket API settings (generic, shared) ---
    skv_test_mode = fields.Boolean(
        string='Skatteverket Test Mode',
        default=True,
        help="Use Skatteverket's test environment instead of production.")

    skv_auth_method = fields.Selection(
        selection=[('cert', 'Certificate'), ('e_id', 'E-identification')],
        string='SKV Auth Method',
        default='cert',
        help="Authentication method for Skatteverket API.")

    skv_auth_url = fields.Char(
        string='SKV Auth URL',
        compute='_compute_skv_auth_url',
        store=True,
        readonly=False,
        help="Skatteverket OAuth2 authorization endpoint.")

    @api.depends('skv_test_mode')
    def _compute_skv_auth_url(self):
        for company in self:
            if not company.skv_auth_url:
                if company.skv_test_mode:
                    company.skv_auth_url = (
                        'https://test.peroauth2.skatteverket.se/'
                        'oauth2/v1/org/authorize')
                else:
                    company.skv_auth_url = (
                        'https://peroauth2.skatteverket.se/'
                        'oauth2/v1/org/authorize')

    skv_token_url = fields.Char(
        string='SKV Token URL',
        compute='_compute_skv_token_url',
        store=True,
        readonly=False,
        help="Skatteverket OAuth2 token endpoint.")

    @api.depends('skv_test_mode')
    def _compute_skv_token_url(self):
        for company in self:
            if not company.skv_token_url:
                if company.skv_test_mode:
                    company.skv_token_url = (
                        'https://test.peroauth2.skatteverket.se/'
                        'oauth2/v1/org/token')
                else:
                    company.skv_token_url = (
                        'https://peroauth2.skatteverket.se/'
                        'oauth2/v1/org/token')
