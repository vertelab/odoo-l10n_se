# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import logging
import os
import tempfile
from uuid import uuid4

import requests
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    # ------------------------------------------------------------------
    # SKV Tax Account fields
    # ------------------------------------------------------------------

    tax_account_last_sync = fields.Datetime(
        string='Last SKV Sync',
        readonly=True,
        help="When tax account transactions were last fetched "
             "from Skatteverket.")

    tax_account_transaction_count = fields.Integer(
        string='SKV Transactions',
        compute='_compute_tax_account_counts', store=True,
        help="Number of imported tax account transactions.")

    tax_account_reconcile_state = fields.Selection(
        selection=[('not_started', 'Not Started'),
                   ('in_progress', 'In Progress'),
                   ('done', 'Fully Reconciled')],
        string='Tax Account Reconciliation',
        compute='_compute_tax_account_state', store=True,
        help="Reconciliation status of the tax account.")

    tax_account_balance = fields.Monetary(
        string='Tax Account Balance (1630)',
        compute='_compute_tax_account_balance',
        help="Current balance of account 1630 (Skattekonto).")

    tax_account_api_balance = fields.Monetary(
        string='SKV Balance',
        compute='_compute_tax_account_api_balance',
        help="Balance reported by Skatteverket API "
             "(from latest fetch).")

    # ------------------------------------------------------------------
    # Computed methods
    # ------------------------------------------------------------------

    @api.depends('company_id')
    def _compute_tax_account_balance(self):
        for journal in self:
            tax_account = self.env['account.account'].search([
                ('company_ids', 'in', [journal.company_id.id]),
                ('code', '=', '1630'),
            ], limit=1)
            journal.tax_account_balance = (
                tax_account.current_balance
                if tax_account else 0.0)

    def _compute_tax_account_api_balance(self):
        for journal in self:
            journal.tax_account_api_balance = 0.0  # populated after fetch

    @api.depends('company_id')
    def _compute_tax_account_counts(self):
        for journal in self:
            statements = self.env['account.bank.statement'].search([
                ('journal_id', '=', journal.id),
                ('skv_ocr_number', '!=', False),
            ])
            journal.tax_account_transaction_count = sum(
                len(s.line_ids) for s in statements)

    @api.depends('company_id')
    def _compute_tax_account_state(self):
        for journal in self:
            statements = self.env['account.bank.statement'].search([
                ('journal_id', '=', journal.id),
                ('skv_ocr_number', '!=', False),
            ])
            if not statements:
                journal.tax_account_reconcile_state = 'not_started'
            elif all(s.reconcile_state == 'done' for s in statements):
                journal.tax_account_reconcile_state = 'done'
            else:
                journal.tax_account_reconcile_state = 'in_progress'

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_open_tax_account_reconciliation(self):
        """Open or create a tax account reconciliation for this journal."""
        self.ensure_one()
        # Find existing open reconciliation or create new
        reconciliation = self.env['tax.account.reconciliation'].search([
            ('journal_id', '=', self.id),
            ('state', '=', 'open'),
        ], limit=1, order='date_from desc')
        if not reconciliation:
            # Create a new one for current month
            today = fields.Date.today()
            date_from = today.replace(day=1)
            date_to = today + relativedelta(months=1, day=1) - relativedelta(
                days=1)
            reconciliation = self.env[
                'tax.account.reconciliation'].create({
                    'journal_id': self.id,
                    'date_from': date_from,
                    'date_to': date_to,
                })
            reconciliation.action_open()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tax Account Reconciliation'),
            'res_model': 'tax.account.reconciliation',
            'view_mode': 'form',
            'res_id': reconciliation.id,
            'target': 'current',
        }

    def action_fetch_tax_account_transactions(self):
        """Fetch transactions from Skatteverket and open reconciliation."""
        self.ensure_one()
        reconciliation = self.env['tax.account.reconciliation'].create({
            'journal_id': self.id,
            'date_from': (self.tax_account_last_sync
                          or fields.Date.today()
                          - relativedelta(days=555)),
            'date_to': fields.Date.today(),
        })
        reconciliation.action_open()
        reconciliation.action_fetch_transactions()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tax Account Reconciliation'),
            'res_model': 'tax.account.reconciliation',
            'view_mode': 'form',
            'res_id': reconciliation.id,
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------

    @api.model
    def _cron_tax_account(self):
        """Daily cron: fetch tax account transactions for all companies."""
        companies = self.env['res.company'].search([])
        for company in companies:
            if not company.skv_skattekonto_api_url:
                continue
            # Refresh token if needed using shared API method
            if company.skv_certificate and not company._check_skv_access_token():
                SkatteverketApi = self.env['skatteverket.api']
                SkatteverketApi.with_company(company)._get_skv_access_token(company)

            # Find moms journal for this company
            moms_journal = self.env['account.journal'].search([
                ('company_id', '=', company.id),
                ('code', '=', 'MOMS'),
            ], limit=1)
            if not moms_journal:
                continue

            today = fields.Date.today()
            reconciliation = self.env[
                'tax.account.reconciliation'].create({
                    'journal_id': moms_journal.id,
                    'date_from': today - relativedelta(days=1),
                    'date_to': today,
                })
            reconciliation.action_open()
            try:
                reconciliation.action_fetch_transactions()
            except Exception as e:
                _logger.warning(
                    "Cron tax account fetch failed for company %s: %s",
                    company.name, e)
