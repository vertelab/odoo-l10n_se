# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # --- Skatteverket API: Environment & Auth ---
    skv_test_mode = fields.Boolean(
        string='Skatteverket Test Mode', default=True,
        help="Use Skatteverket's test environment instead of production.")

    skv_auth_method = fields.Selection(
        selection=[('cert', 'Certificate'), ('e_id', 'E-identification')],
        string='SKV Auth Method', default='cert',
        help="Authentication method for Skatteverket API.")

    skv_certificate = fields.Binary(
        string='Certificate (PEM)', attachment=False,
        help="Upload the certificate file (.pem) for Skatteverket API authentication.")

    skv_certificate_pin = fields.Char(
        string='Certificate PIN',
        help="PIN code for the certificate, if required.")

    # --- OAuth2 endpoints (computed with test/live default) ---
    skv_auth_url = fields.Char(
        string='SKV Auth URL',
        compute='_compute_skv_auth_url', store=True, readonly=False,
        help="Skatteverket OAuth2 authorization endpoint.")

    @api.depends('skv_test_mode')
    def _compute_skv_auth_url(self):
        for company in self:
            if not company.skv_auth_url:
                if company.skv_test_mode:
                    company.skv_auth_url = 'https://test.peroauth2.skatteverket.se/oauth2/v1/org/authorize'
                else:
                    company.skv_auth_url = 'https://peroauth2.skatteverket.se/oauth2/v1/org/authorize'

    skv_token_url = fields.Char(
        string='SKV Token URL',
        compute='_compute_skv_token_url', store=True, readonly=False,
        help="Skatteverket OAuth2 token endpoint.")

    @api.depends('skv_test_mode')
    def _compute_skv_token_url(self):
        for company in self:
            if not company.skv_token_url:
                if company.skv_test_mode:
                    company.skv_token_url = 'https://test.peroauth2.skatteverket.se/oauth2/v1/org/token'
                else:
                    company.skv_token_url = 'https://peroauth2.skatteverket.se/oauth2/v1/org/token'

    # --- OAuth2 token storage ---
    skv_authorization_code = fields.Char(string='SKV Authorization Code', readonly=True)
    skv_access_token = fields.Char(string='SKV Access Token', readonly=True)
    skv_recived_token_on = fields.Datetime(string='SKV Token Received On', readonly=True)
    skv_expires_in = fields.Integer(string='SKV Token Expires In (seconds)', readonly=True)
    skv_oauth_client_id = fields.Char(string='SKV OAuth Client ID')
    skv_oauth_secret = fields.Char(string='SKV OAuth Client Secret')

    def _check_skv_access_token(self):
        """Check if the stored access token is still valid."""
        if (self.skv_access_token
                and self.skv_recived_token_on
                and self.skv_recived_token_on
                + relativedelta(seconds=self.skv_expires_in)
                > fields.Datetime.now()):
            return True
        return False

    # --- Service endpoints (computed with test/live default) ---
    skv_moms_api_url = fields.Char(
        string='SKV Moms API URL',
        compute='_compute_skv_service_urls', store=True, readonly=False,
        help="Skatteverket API endpoint for VAT declarations.")

    skv_pc_api_url = fields.Char(
        string='SKV PC API URL',
        compute='_compute_skv_service_urls', store=True, readonly=False,
        help="Skatteverket API endpoint for periodic compilation (EU sales list).")

    skv_skattekonto_api_url = fields.Char(
        string='SKV Skattekonto API URL',
        compute='_compute_skv_service_urls', store=True, readonly=False,
        help="Skatteverket API endpoint for tax account transactions.")

    skv_agd_api_url = fields.Char(
        string='SKV AGD API URL',
        compute='_compute_skv_service_urls', store=True, readonly=False,
        help="Skatteverket API endpoint for employer declarations (AGD).")

    @api.depends('skv_test_mode')
    def _compute_skv_service_urls(self):
        for company in self:
            if not company.skv_moms_api_url:
                company.skv_moms_api_url = (
                    'https://test.api.skatteverket.se/moms/v2/deklaration'
                    if company.skv_test_mode else
                    'https://api.skatteverket.se/moms/v2/deklaration')
            if not company.skv_pc_api_url:
                company.skv_pc_api_url = (
                    'https://test.api.skatteverket.se/moms/v2/periodsammandrag'
                    if company.skv_test_mode else
                    'https://api.skatteverket.se/moms/v2/periodsammandrag')
            if not company.skv_skattekonto_api_url:
                company.skv_skattekonto_api_url = (
                    'https://test.api.skatteverket.se/skattekonto/v2'
                    if company.skv_test_mode else
                    'https://api.skatteverket.se/skattekonto/v2')
            if not company.skv_agd_api_url:
                company.skv_agd_api_url = (
                    'https://test.api.skatteverket.se/arbetsgivare/v2/deklaration'
                    if company.skv_test_mode else
                    'https://api.skatteverket.se/arbetsgivare/v2/deklaration')
