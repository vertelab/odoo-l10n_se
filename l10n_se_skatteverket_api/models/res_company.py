# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # --- Skatteverket API settings ---
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

    # --- Per-service API URLs (computed) ---
    skv_moms_api_url = fields.Char(
        string='SKV Moms API URL',
        compute='_compute_skv_service_urls',
        store=True,
        readonly=False,
        help="Skatteverket API endpoint for VAT declarations.")

    skv_pc_api_url = fields.Char(
        string='SKV PC API URL',
        compute='_compute_skv_service_urls',
        store=True,
        readonly=False,
        help="Skatteverket API endpoint for periodic compilation (EU sales list).")

    skv_skattekonto_api_url = fields.Char(
        string='SKV Tax Account API URL',
        compute='_compute_skv_service_urls',
        store=True,
        readonly=False,
        help="Skatteverket API endpoint for tax account transactions.")

    @api.depends('skv_test_mode')
    def _compute_skv_service_urls(self):
        for company in self:
            if not company.skv_moms_api_url:
                if company.skv_test_mode:
                    company.skv_moms_api_url = (
                        'https://test.api.skatteverket.se/moms/v2/deklaration')
                else:
                    company.skv_moms_api_url = (
                        'https://api.skatteverket.se/moms/v2/deklaration')
            if not company.skv_pc_api_url:
                if company.skv_test_mode:
                    company.skv_pc_api_url = (
                        'https://test.api.skatteverket.se/moms/v2/periodsammandrag')
                else:
                    company.skv_pc_api_url = (
                        'https://api.skatteverket.se/moms/v2/periodsammandrag')
            if not company.skv_skattekonto_api_url:
                if company.skv_test_mode:
                    company.skv_skattekonto_api_url = (
                        'https://test.api.skatteverket.se/skattekonto/v2')
                else:
                    company.skv_skattekonto_api_url = (
                        'https://api.skatteverket.se/skattekonto/v2')
