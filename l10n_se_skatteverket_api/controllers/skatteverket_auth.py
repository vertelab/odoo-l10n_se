# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)


class SkatteverketAuth(http.Controller):

    @http.route('/skatteverket/auth', type='http', auth='public', website=True)
    def authenticate(self, **kw):
        """OAuth2 callback for Skatteverket e-ID authentication."""
        state = kw.get('state')
        auth_code = kw.get('code')

        if not state or not auth_code:
            _logger.warning(
                "SKV auth callback missing state or code: %s", kw)
            return request.redirect('/web')

        # Try tax.account.reconciliation (l10n_se_tax_account module)
        rec_model = request.env.get('tax.account.reconciliation')
        if rec_model:
            reconciliation = rec_model.sudo().search(
                [('api_state', '=', state)], limit=1)
            if reconciliation:
                partner = reconciliation._get_skv_partner()
                if partner:
                    partner.authorization_code = auth_code
                    token = reconciliation._get_skv_access_token(partner)
                    if token:
                        return request.redirect(
                            '/web#id=%s&model=tax.account.reconciliation'
                            '&view_type=form' % reconciliation.id)

        # Fallback: journal-based flow
        journal = request.env['account.journal'].sudo().search(
            [('api_state', '=', state)], limit=1)
        if journal:
            partner = request.env['res.partner'].sudo().search(
                [('enable_skatteverket_api', '=', True)], limit=1)
            if partner:
                partner.authorization_code = auth_code

        return request.redirect('/web')
