# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
import requests

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class TaxAccountTransactionWizard(models.TransientModel):
    _name = 'tax_account.transaction.wizard'
    _description = "Fetch Tax Account Transactions"

    journal_id = fields.Many2one(
        comodel_name='account.journal', required=True,
        string='Tax Journal')
    date_from = fields.Date(
        string='From Date',
        help="Start date for fetching transactions. "
             "Defaults to last sync date or 555 days ago.",
        default=lambda self: self._default_date_from())

    def _default_date_from(self):
        """Default to last sync date, or 555 days ago."""
        journal = self.env['account.journal'].browse(
            self.env.context.get('default_journal_id'))
        if journal and journal.tax_account_last_sync:
            return journal.tax_account_last_sync
        return fields.Date.today() - __import__(
            'dateutil.relativedelta',
            fromlist=['relativedelta']
        ).relativedelta(days=555)

    def get_transactions(self):
        """Fetch transactions and open reconciliation view."""
        self.ensure_one()
        journal = self.journal_id
        if not journal:
            raise UserError(_("No journal selected."))

        partner = self.env['res.partner'].search(
            [('enable_skatteverket_api', '=', True)], limit=1)
        if not partner:
            partner = self.env.ref(
                'l10n_se_tax_report.res_partner-SKV',
                raise_if_not_found=False)
        if not partner:
            raise UserError(_(
                "No Skatteverket partner configured. "
                "Create a partner with 'Enable Skatteverket API' "
                "checked."))

        if not partner.check_valid_access_token():
            raise UserError(_(
                "No valid access token. "
                "Please authorize first on the journal."))

        # Create reconciliation and fetch
        reconciliation = self.env['tax.account.reconciliation'].create({
            'journal_id': journal.id,
            'date_from': self.date_from,
            'date_to': fields.Date.today(),
        })
        reconciliation.action_open()
        try:
            reconciliation.action_fetch_transactions()
        except Exception as e:
            _logger.error("Failed to fetch transactions: %s", e)
            raise UserError(_(
                "Failed to fetch transactions from Skatteverket:\n%s")
                % str(e))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tax Account Reconciliation'),
            'res_model': 'tax.account.reconciliation',
            'view_mode': 'form',
            'res_id': reconciliation.id,
            'target': 'current',
        }
