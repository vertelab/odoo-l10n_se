# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
import os
import tempfile
from uuid import uuid4

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class SkatteverketApi(models.AbstractModel):
    """Shared Skatteverket API methods.

    All configuration is read from res.company (self._get_skv_company()).
    """
    _name = 'skatteverket.api'
    _description = 'Skatteverket API Shared Methods'

    # ------------------------------------------------------------------
    # Helpers: company settings
    # ------------------------------------------------------------------

    def _get_skv_settings(self):
        """Retrieve Skatteverket API settings from company."""
        company = self._get_skv_company()
        return {
            'test_mode': company.skv_test_mode,
            'auth_method': company.skv_auth_method,
            'auth_url': company.skv_auth_url,
            'token_url': company.skv_token_url,
        }

    def _get_skv_company(self):
        """Return the company for API calls. Override in subclasses."""
        return self.env.company

    def _get_skv_partner(self):
        """Find a partner for reference (legacy). All config on company now."""
        partner = self.env.ref(
            'l10n_se_skatteverket_api.res_partner_skv',
            raise_if_not_found=False)
        return partner

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def _get_skv_access_token(self, company=None):
        """Obtain an access token for Skatteverket API.

        Uses certificate-based OAuth2 client credentials flow.
        Returns cached token if still valid.
        """
        if company is None:
            company = self._get_skv_company()

        if company._check_skv_access_token():
            return company.skv_access_token

        settings = self._get_skv_settings()

        if settings['auth_method'] == 'cert':
            if not company.skv_certificate:
                raise UserError(_(
                    "No certificate configured. "
                    "Upload a certificate in Skatteverket API settings."))
            return self._authenticate_with_cert(company, settings)
        else:
            raise UserError(_(
                "E-identification flow requires interactive browser. "
                "Please use certificate authentication or complete "
                "OAuth2 authorization first."))

    def _authenticate_with_cert(self, company, settings=None):
        """Authenticate using certificate-based client credentials.

        Returns the access token string and stores it on the company.
        """
        if settings is None:
            settings = self._get_skv_settings()

        cert_data = base64.b64decode(company.skv_certificate)
        tmp = tempfile.NamedTemporaryFile(suffix='.pem', delete=False)
        tmp.write(cert_data)
        tmp.close()
        session = requests.Session()
        session.cert = tmp.name
        try:
            resp = session.post(
                settings['token_url'],
                data={
                    'grant_type': 'client_credentials',
                    'client_id': partner.oauth_client_id or '',
                    'client_secret': partner.oauth_secret or '',
                    'scope': 'ska',
                },
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                timeout=30,
            )
            if resp.status_code == 200:
                token_data = resp.json()
                partner.write({
                    'access_token': token_data.get('access_token'),
                    'recived_token_on': fields.Datetime.now(),
                    'expires_in': token_data.get('expires_in', 3600),
                })
                return token_data.get('access_token')
            else:
                _logger.error(
                    "SKV token error: %s %s",
                    resp.status_code, resp.text[:500])
                raise UserError(_(
                    "Failed to get access token from Skatteverket: %s")
                    % resp.text[:200])
        finally:
            os.unlink(tmp.name)

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    def _build_skv_headers(self, access_token, content_type=None):
        """Build standard HTTP headers for Skatteverket API calls.

        Args:
            access_token (str): OAuth2 bearer token.
            content_type (str, optional): Content-Type header value.
                Defaults to 'application/json'.

        Returns:
            dict: HTTP headers.
        """
        headers = {
            'Authorization': 'Bearer %s' % access_token,
            'SKV-client_correlationid': str(uuid4()),
            'Accept': 'application/json',
        }
        if content_type:
            headers['Content-Type'] = content_type
        return headers

    # ------------------------------------------------------------------
    # API call helper
    # ------------------------------------------------------------------

    def _skv_api_call(self, url, xml_bytes=None, method='POST',
                      access_token=None, service_type='moms'):
        """Make an authenticated API call to Skatteverket.

        Args:
            url (str): Full API endpoint URL.
            xml_bytes (bytes, optional): XML payload for POST.
            method (str): HTTP method ('POST' or 'GET').
            access_token (str, optional): Bearer token. If omitted,
                will fetch using company config.
            service_type (str): Service type for error context.

        Returns:
            requests.Response: The API response.
        """
        if not access_token:
            access_token = self._get_skv_access_token()

        content_type = (
            'application/xml; charset=ISO-8859-1'
            if xml_bytes else None)
        headers = self._build_skv_headers(access_token, content_type)

        try:
            if method == 'GET':
                response = requests.get(
                    url, headers=headers, timeout=30)
            else:
                response = requests.post(
                    url, data=xml_bytes, headers=headers, timeout=30)

            _logger.info(
                "SKV API %s %s: %s %s",
                method, url, response.status_code,
                response.text[:500])

            return response

        except requests.exceptions.RequestException as e:
            raise UserError(_(
                "Could not connect to Skatteverket API (%s):\n%s")
                % (service_type, str(e)))

    # ------------------------------------------------------------------
    # Response handler
    # ------------------------------------------------------------------

    def _handle_skv_response(self, response, company=None):
        """Handle Skatteverket API response and update status fields.

        Args:
            response (requests.Response): The API response.
            company (res.company, optional): For clearing expired tokens.

        Returns:
            dict: Status info with keys: status ('accepted'|'error'),
                  response_text, submitted_date.
        """
        if response.status_code in (200, 201, 202):
            return {
                'skv_api_status': 'accepted',
                'skv_response': 'OK: %s' % response.text[:500],
                'skv_submitted_date': fields.Datetime.now(),
            }
        elif response.status_code == 401:
            if company:
                company.write({'skv_access_token': False})
            raise UserError(_(
                "Authentication failed. Token may have expired. "
                "Please retry the submission."))
        else:
            raise UserError(_(
                "Skatteverket API returned error %s:\n%s")
                % (response.status_code, response.text[:500]))
