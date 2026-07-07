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

        company = journal.company_id or self.env.company
        if not company._check_skv_access_token():
            raise UserError(_(
                "No valid access token. "
                "Please authorize first via Accounting > Configuration "
                "> Skatteverket API settings."))

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
