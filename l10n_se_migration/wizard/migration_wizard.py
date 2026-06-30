# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
import io
import csv
import json

_logger = logging.getLogger(__name__)

SOURCE_SYSTEMS = [
    ('fortnox', 'Fortnox'),
    ('visma', 'Visma Spiris / eEkonomi'),
    ('bokio', 'Bokio'),
    ('sie', 'SIE file (generic)'),
]


class MigrationWizard(models.TransientModel):
    """Wizard to guide migration from competing accounting systems to Odoo."""

    _name = 'l10n_se.migration.wizard'
    _description = 'Migration Wizard'

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company,
    )
    source_system = fields.Selection(
        SOURCE_SYSTEMS, string='Source System', required=True,
    )
    sie_file = fields.Binary(
        string='SIE File', help='Upload SIE export from source system.',
    )
    sie_filename = fields.Char(string='SIE Filename')

    # Fortnox-specific
    fortnox_client_id = fields.Char(string='Fortnox Client ID')
    fortnox_client_secret = fields.Char(string='Fortnox Client Secret')
    fortnox_access_token = fields.Char(string='Access Token')
    fortnox_fiscal_year = fields.Integer(string='Fiscal Year to Import')

    # Options
    import_chart_of_accounts = fields.Boolean(string='Import Chart of Accounts', default=True)
    import_journal_entries = fields.Boolean(string='Import Journal Entries', default=True)
    import_partners = fields.Boolean(string='Import Customers/Suppliers', default=True)
    import_invoices = fields.Boolean(string='Import Invoices', default=False)
    import_opening_balance = fields.Boolean(string='Import Opening Balances', default=True)

    # Results
    state = fields.Selection(
        selection=[
            ('select', 'Select Source'),
            ('upload', 'Upload Data'),
            ('mapping', 'Map Accounts'),
            ('import', 'Importing'),
            ('done', 'Done'),
        ],
        default='select',
    )
    imported_accounts = fields.Integer(string='Accounts Imported', readonly=True)
    imported_entries = fields.Integer(string='Journal Entries Imported', readonly=True)
    imported_partners = fields.Integer(string='Partners Imported', readonly=True)
    imported_invoices = fields.Integer(string='Invoices Imported', readonly=True)
    result_log = fields.Text(string='Import Log', readonly=True)

    # ------------------------------------------------------------------
    # Step 1: Select source
    # ------------------------------------------------------------------

    def action_select_source(self):
        """Move to upload/authenticate step."""
        self.ensure_one()
        if not self.source_system:
            raise UserError(_('Please select a source system.'))
        self.state = 'upload'
        return self._reopen_wizard()

    # ------------------------------------------------------------------
    # Step 2: Upload data
    # ------------------------------------------------------------------

    def action_upload_data(self):
        """Validate uploaded data and move to mapping."""
        self.ensure_one()
        if self.source_system == 'fortnox':
            self._validate_fortnox()
        elif self.source_system in ('visma', 'bokio', 'sie'):
            self._validate_sie()
        self.state = 'mapping'
        return self._reopen_wizard()

    def _validate_fortnox(self):
        """Test Fortnox API connection."""
        if not self.fortnox_access_token:
            raise UserError(_('Please provide a Fortnox Access Token.'))

        # Test connection
        provider = FortnoxProvider(self.fortnox_access_token)
        try:
            provider.test_connection()
            self.result_log = 'Fortnox connection successful.\n'
            if self.fortnox_fiscal_year:
                self.result_log += 'Will import fiscal year %s.\n' % self.fortnox_fiscal_year
        except Exception as e:
            raise UserError(_('Fortnox connection failed: %s') % e)

    def _validate_sie(self):
        """Validate SIE file content."""
        if not self.sie_file:
            raise UserError(_('Please upload a SIE file.'))

        content = base64.b64decode(self.sie_file).decode('utf-8', errors='replace')
        # Basic SIE validation
        lines = content.split('\n')
        if not any(l.startswith('#FLAGGA') for l in lines):
            raise UserError(_('Invalid SIE file: missing #FLAGGA header.'))

        has_accounts = any(l.startswith('#KONTO') for l in lines)
        has_entries = any(l.startswith('#VER') or l.startswith('#TRANS') for l in lines)

        self.result_log = 'SIE file validated.\n'
        if has_accounts:
            self.result_log += '- Contains chart of accounts\n'
        if has_entries:
            self.result_log += '- Contains journal entries\n'
        # Count entries
        ver_count = sum(1 for l in lines if l.startswith('#VER'))
        trans_count = sum(1 for l in lines if l.startswith('#TRANS'))
        self.result_log += '- %d verifications, %d transactions\n' % (ver_count, trans_count)

    # ------------------------------------------------------------------
    # Step 3: Map and import
    # ------------------------------------------------------------------

    def action_import(self):
        """Execute the migration."""
        self.ensure_one()
        self.state = 'import'
        log_lines = []

        if self.source_system == 'fortnox':
            log_lines = self._import_fortnox()
        elif self.source_system in ('visma', 'bokio', 'sie'):
            log_lines = self._import_sie()

        self.state = 'done'
        self.result_log = '\n'.join(log_lines)
        return self._reopen_wizard()

    def _import_fortnox(self):
        """Import data from Fortnox via API."""
        log = []
        provider = FortnoxProvider(self.fortnox_access_token)

        try:
            if self.import_chart_of_accounts:
                accounts = provider.fetch_accounts()
                count = self._import_fortnox_accounts(accounts)
                self.imported_accounts = count
                log.append('Accounts imported: %d' % count)

            if self.import_partners:
                customers = provider.fetch_customers()
                suppliers = provider.fetch_suppliers()
                cust_count = self._import_partners(customers, 'customer')
                supp_count = self._import_partners(suppliers, 'supplier')
                self.imported_partners = cust_count + supp_count
                log.append('Customers imported: %d' % cust_count)
                log.append('Suppliers imported: %d' % supp_count)

            if self.import_invoices:
                invoices = provider.fetch_invoices()
                inv_count = self._import_fortnox_invoices(invoices)
                self.imported_invoices = inv_count
                log.append('Invoices imported: %d' % inv_count)

            if self.import_journal_entries:
                vouchers = provider.fetch_vouchers(self.fortnox_fiscal_year)
                count = self._import_fortnox_vouchers(vouchers)
                self.imported_entries = count
                log.append('Journal entries imported: %d' % count)

        except Exception as e:
            log.append('ERROR: %s' % e)
            _logger.exception('Fortnox import failed')

        return log

    def _import_sie(self):
        """Import data from SIE file using existing l10n_se_sie infrastructure."""
        log = []
        if not self.sie_file:
            log.append('ERROR: No SIE file uploaded.')
            return log

        try:
            SieImport = self.env['l10n_se.sie.import']
            data_file = base64.b64decode(self.sie_file)

            # Import accounts
            if self.import_chart_of_accounts:
                account_count = SieImport._import_sie_accounts(data_file, self.company_id)
                self.imported_accounts = account_count
                log.append('Accounts imported: %d' % account_count)

            # Import partners from SIE objects
            if self.import_partners:
                partner_count = SieImport._import_sie_objects(data_file, self.company_id)
                self.imported_partners = partner_count
                log.append('Partners imported: %d' % partner_count)

            # Import journal entries (verifications)
            if self.import_journal_entries:
                entry_count = SieImport._import_sie_verifications(
                    data_file, self.company_id,
                    import_opening=self.import_opening_balance,
                )
                self.imported_entries = entry_count
                log.append('Journal entries imported: %d' % entry_count)

        except Exception as e:
            log.append('ERROR: %s' % e)
            _logger.exception('SIE import failed')

        return log

    # ------------------------------------------------------------------
    # Import helpers
    # ------------------------------------------------------------------

    def _import_fortnox_accounts(self, accounts):
        """Create account.account records from Fortnox data."""
        count = 0
        account_model = self.env['account.account'].with_company(self.company_id.id)
        for acct in accounts:
            existing = account_model.search([
                ('code', '=', str(acct['number'])),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if existing:
                continue
            vals = {
                'code': str(acct['number']),
                'name': acct.get('description', ''),
                'account_type': self._map_fortnox_account_type(acct.get('type', '')),
                'company_id': self.company_id.id,
            }
            account_model.create(vals)
            count += 1
        return count

    def _import_partners(self, partners, partner_type):
        """Create res.partner records."""
        count = 0
        partner_model = self.env['res.partner'].with_company(self.company_id.id)
        type_label = 'invoice' if partner_type == 'customer' else 'purchase'

        for partner in partners:
            org_nr = partner.get('organisation_number', '').replace('-', '')
            existing = partner_model.search([
                ('vat', 'ilike', org_nr),
                ('company_id', '=', self.company_id.id),
            ], limit=1) if org_nr else None

            if existing:
                continue

            vals = {
                'name': partner.get('name', 'Unknown'),
                'vat': org_nr,
                'company_id': self.company_id.id,
                'is_company': True,
                'customer_rank': 1 if partner_type == 'customer' else 0,
                'supplier_rank': 1 if partner_type == 'supplier' else 0,
                supplier_rank=1 if partner_type == 'supplier' else 1,
            }
            partner_model.create(vals)
            count += 1
        return count

    def _import_fortnox_vouchers(self, vouchers):
        """Create account.move records from Fortnox vouchers."""
        count = 0
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            _logger.warning('No general journal found, skipping voucher import')
            return 0

        move_model = self.env['account.move'].with_company(self.company_id.id)
        for voucher in vouchers:
            lines = []
            for row in voucher.get('rows', []):
                account = self.env['account.account'].search([
                    ('code', '=', str(row.get('account', 0))),
                    ('company_id', '=', self.company_id.id),
                ], limit=1)
                if not account:
                    continue
                lines.append((0, 0, {
                    'account_id': account.id,
                    'debit': float(row.get('debit', 0)),
                    'credit': float(row.get('credit', 0)),
                    'name': row.get('description', ''),
                }))

            if lines:
                move = move_model.create({
                    'journal_id': journal.id,
                    'date': voucher.get('date', fields.Date.today()),
                    'ref': 'Fortnox: %s' % voucher.get('voucher_number', ''),
                    'line_ids': lines,
                })
                move.action_post()
                count += 1

        return count

    def _import_fortnox_invoices(self, invoices):
        """Create account.move records for invoices."""
        count = 0
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            return 0

        move_model = self.env['account.move'].with_company(self.company_id.id)
        for inv in invoices:
            # Simplified invoice import — full version needs product/account mapping
            partner = self._find_partner_by_vat(inv.get('customer_number', ''))
            if not partner:
                continue

            move = move_model.create({
                'move_type': 'out_invoice',
                'journal_id': journal.id,
                'partner_id': partner.id,
                'invoice_date': inv.get('invoice_date', fields.Date.today()),
                'ref': 'Fortnox Invoice: %s' % inv.get('document_number', ''),
                # Line items would need proper product/tax mapping
            })
            count += 1
        return count

    def _find_partner_by_vat(self, vat):
        """Find partner by VAT number."""
        if not vat:
            return None
        vat = vat.replace('-', '').replace('SE', '')
        return self.env['res.partner'].search([
            ('vat', 'ilike', vat),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

    def _map_fortnox_account_type(self, fortnox_type):
        """Map Fortnox account type to Odoo account type."""
        mapping = {
            'ASSET': 'asset_fixed',
            'LIABILITY': 'liability_non_current',
            'REVENUE': 'income',
            'COST': 'expense',
            'EQUITY': 'equity',
        }
        return mapping.get(fortnox_type.upper(), 'asset_current')

    def _reopen_wizard(self):
        """Return action to reopen the wizard at current state."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }


# ==================================================================
# Fortnox API Provider
# ==================================================================

class FortnoxProvider:
    """Minimal Fortnox API client for data export/migration.

    Uses Fortnox REST API v3 with OAuth2 access token.
    Documented at: https://developer.fortnox.se/
    """

    BASE_URL = 'https://api.fortnox.se/3'

    def __init__(self, access_token, client_secret=None):
        self.access_token = access_token
        self.client_secret = client_secret
        self.session = self._build_session()

    def _build_session(self):
        import requests
        session = requests.Session()
        session.headers.update({
            'Authorization': 'Bearer %s' % self.access_token,
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        })
        if self.client_secret:
            session.headers['Client-Secret'] = self.client_secret
        return session

    def test_connection(self):
        """Verify the API connection works."""
        resp = self.session.get('%s/companyinformation' % self.BASE_URL)
        resp.raise_for_status()
        return resp.json()

    def fetch_accounts(self):
        """Fetch chart of accounts from Fortnox."""
        accounts = []
        page = 1
        while True:
            resp = self.session.get('%s/accounts' % self.BASE_URL, params={'page': page})
            resp.raise_for_status()
            data = resp.json()
            for acct in data.get('Accounts', []):
                accounts.append({
                    'number': acct['Number'],
                    'description': acct.get('Description', ''),
                    'type': acct.get('Type', ''),
                    'sru_code': acct.get('SRU', ''),
                })
            if len(data.get('Accounts', [])) < 100:
                break
            page += 1
        return accounts

    def fetch_customers(self):
        """Fetch customers from Fortnox."""
        return self._fetch_list('customers', 'Customers')

    def fetch_suppliers(self):
        """Fetch suppliers from Fortnox."""
        return self._fetch_list('suppliers', 'Suppliers')

    def fetch_invoices(self):
        """Fetch customer invoices from Fortnox."""
        return self._fetch_list('invoices', 'Invoices')

    def fetch_vouchers(self, fiscal_year=None):
        """Fetch vouchers (journal entries) from Fortnox."""
        return self._fetch_list('vouchers', 'Vouchers')

    def _fetch_list(self, endpoint, key):
        """Generic paginated fetch helper."""
        items = []
        page = 1
        while True:
            resp = self.session.get('%s/%s' % (self.BASE_URL, endpoint), params={'page': page})
            resp.raise_for_status()
            data = resp.json()
            items.extend(data.get(key, []))
            if len(data.get(key, [])) < 100:
                break
            page += 1
        return items
