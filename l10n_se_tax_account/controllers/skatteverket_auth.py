# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class SkatteverketAuth(http.Controller):

    @http.route('/skattekonto', type='http', auth='public', website=True)
    def authenticate_tax_account(self, **kw):
        """OAuth2 callback for Skatteverket e-ID authentication."""
        state = kw.get('state')
        auth_code = kw.get('code')

        partner_env = request.env['res.partner'].sudo()

        if not state or not auth_code:
            _logger.warning(
                "SKV auth callback missing state or code: %s", kw)
            return request.redirect('/web')

        # Find the reconciliation session by API state
        reconciliation = request.env[
            'tax.account.reconciliation'].sudo().search(
                [('api_state', '=', state)], limit=1)

        if reconciliation:
            partner = reconciliation._get_skv_partner()
            if partner:
                partner.authorization_code = auth_code
                # Exchange code for token
                token = reconciliation._get_skv_access_token(partner)
                if token:
                    return request.redirect(
                        '/web#id=%s&model=tax.account.reconciliation'
                        '&view_type=form' % reconciliation.id)

        # Fallback: legacy journal-based flow
        journal_env = request.env['account.journal'].sudo()
        journal = journal_env.search(
            [('api_state', '=', state)], limit=1)
        if journal:
            partner = journal._get_skv_partner()
            if partner:
                partner.authorization_code = auth_code
                reconciliation = request.env[
                    'tax.account.reconciliation'].sudo().search(
                        [('journal_id', '=', journal.id),
                         ('state', '=', 'draft')],
                        limit=1)
                if reconciliation:
                    token = reconciliation._get_skv_access_token(partner)
                    if token:
                        return request.redirect(
                            '/web#id=%s&model=tax.account.reconciliation'
                            '&view_type=form' % reconciliation.id)

        return request.redirect('/web')
