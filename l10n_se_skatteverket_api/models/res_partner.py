# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    enable_skatteverket_api = fields.Boolean(
        string='Enable Skatteverket API')
    certificate = fields.Binary(
        string='Certificate (PEM)',
        attachment=False,
        help="Upload the certificate file (.pem) for Skatteverket API "
             "authentication.")
    certificate_pin = fields.Char(
        string='Certificate PIN',
        help="PIN code for the certificate, if required.")

    # OAuth2 token storage
    authorization_code = fields.Char(
        string='Authorization Code', readonly=True)
    access_token = fields.Char(
        string='Access Token', readonly=True)
    recived_token_on = fields.Datetime(
        string='Token Received On', readonly=True)
    expires_in = fields.Integer(
        string='Token Expires In (seconds)', readonly=True)
    oauth_client_id = fields.Char(
        string='OAuth Client ID')
    oauth_secret = fields.Char(
        string='OAuth Client Secret')

    def check_valid_access_token(self):
        """Check if the stored access token is still valid."""
        self.ensure_one()
        if (self.access_token
                and self.recived_token_on
                and self.recived_token_on
                + relativedelta(seconds=self.expires_in)
                > fields.Datetime.now()):
            return True
        return False
