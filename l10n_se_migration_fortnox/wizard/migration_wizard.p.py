# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<http://vertel.se>).
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import base64
import io
import csv
import json

from ..providers.fortnox_provider import FortnoxProvider, FortnoxError

_logger = logging.getLogger(__name__)

SOURCE_SYSTEMS = [
    ('fortnox', 'Fortnox'),
    ('visma', 'Visma Spiris / eEkonomi'),
    ('bokio', 'Bokio'),
    ('sie', 'SIE file (generic)'),
]


class MigrationWizard(models.TransientModel):
    """Wizard to guide migration from competing accounting systems to Odoo."""

    _name = 'l10n_se.fortnox.migration.wizard'
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

    # Fortnox: SIE 4 som primärväg
    fortnox_use_sie = fields.Boolean(
        string='Använd SIE 4 (rekommenderat)',
        default=True,
        help='SIE 4 ger kontoplan, ingående balans och alla verifikationer i '
             'ett anrop. Komplettera med API:t för kunder, leverantörer och '
             'faktura-PDF:er.',
    )
    fortnox_export_pdf = fields.Boolean(
        string='Hämta faktura-PDF:er', default=True,
    )
    fortnox_dry_run = fields.Boolean(
        string='Endast förhandsgranska', default=False,
        help='Tolka filen och rapportera vad som skulle importeras, utan att '
             'skriva något i databasen.',
    )
    sie_report = fields.Text(string='SIE-rapport', readonly=True)

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
        provider = FortnoxProvider(
            self.fortnox_access_token, self.fortnox_client_secret,
        )
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

    def action_back_to_select(self):
        """Return to step 1 (select source)."""
        self.ensure_one()
        self.state = 'select'
        return self._reopen_wizard()

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
        """Import data from Fortnox via API.

        Ordningen är viktig: konton och journaler FÖRST, sedan partners,
        sist bokföring. Annars finns inget att kontera mot.
        """
        log = []
        self.provider = FortnoxProvider(
            self.fortnox_access_token, self.fortnox_client_secret,
        )

        try:
            # Steg 1: konton + journaler (förutsättning för allt annat)
            if self.import_chart_of_accounts:
                accounts = self.provider.fetch_accounts()
                count = self._import_fortnox_accounts(accounts)
                self.imported_accounts = count
                log.append('Konton skapade: %d' % count)

            series = self.provider.fetch_voucher_series()
            j_count = 0
            resolver = self.env['l10n_se.fortnox.migration.account.resolver']
            for s in series:
                if not s.get('Code'):
                    continue
                _, created = resolver.resolve_journal(
                    s['Code'], name=s.get('Description'), company=self.company_id,
                )
                if created:
                    j_count += 1
            log.append('Journaler skapade: %d' % j_count)

            # Steg 2: partners
            if self.import_partners:
                customers = self.provider.fetch_customers()
                suppliers = self.provider.fetch_suppliers()
                cust_count = self._import_partners(customers, 'customer')
                supp_count = self._import_partners(suppliers, 'supplier')
                self.imported_partners = cust_count + supp_count
                log.append('Kunder: %d' % cust_count)
                log.append('Leverantörer: %d' % supp_count)

            # Steg 3: bokföring — SIE 4 är primärväg
            if self.fortnox_use_sie and self.import_journal_entries:
                fy = self.fortnox_fiscal_year
                log.append('Hämtar SIE 4 (räkenskapsår %s)...' % (fy or 'senaste'))
                try:
                    blob = self.provider.fetch_sie(
                        sie_type=4, financial_year=fy or None,
                    )
                except FortnoxError as e:
                    log.append('SIE-hämtning misslyckades: %s' % e)
                    log.append('Faller tillbaka på API-verifikationer.')
                    blob = None

                if blob:
                    importer = self.env['l10n_se.fortnox.migration.sie.importer']
                    report = importer.import_sie(
                        blob,
                        company=self.company_id,
                        options={
                            'import_accounts': self.import_chart_of_accounts,
                            'import_opening': self.import_opening_balance,
                            'import_vouchers': True,
                            'dry_run': self.fortnox_dry_run,
                        },
                    )
                    self.imported_entries = report['vouchers_created']
                    log.append('SIE-teckenkodning: %s' % report['encoding'])
                    log.append('SIE-typ: %s' % report['sie_type'])
                    log.append('Konton skapade via SIE: %d'
                               % len(report['accounts_created']))
                    log.append('Ingående balans: %d rader'
                               % report['opening_created'])
                    log.append('Verifikationer via SIE: %d'
                               % report['vouchers_created'])
                    if report['vouchers_skipped']:
                        log.append('Överhoppade: %d'
                                   % report['vouchers_skipped'])
                    if report.get('dry_run'):
                        log.append('--- FÖRHANDSGRANSKNING ---')
                    for prob in report['problems'][:20]:
                        log.append('  ! %s' % prob)
                    for err in report['errors'][:20]:
                        log.append('  x %s' % err)

            elif self.import_journal_entries:
                # Reservväg: verifikationer via API
                vouchers = self.provider.fetch_vouchers(self.fortnox_fiscal_year)
                count = self._import_fortnox_vouchers(vouchers)
                self.imported_entries = count
                log.append('Verifikationer via API: %d' % count)

            # Steg 4: fakturor + PDF
            invoices = []
            if self.import_invoices or self.fortnox_export_pdf:
                invoices = self.provider.fetch_invoices()

            if self.import_invoices:
                inv_count = self._import_fortnox_invoices(invoices)
                self.imported_invoices = inv_count
                log.append('Fakturor: %d' % inv_count)

            if self.fortnox_export_pdf:
                pdf = self.env['l10n_se.fortnox.migration.pdf']
                rep = pdf.export_customer_invoices(
                    self.provider, invoices,
                    company=self.company_id, dry_run=self.fortnox_dry_run,
                )
                log.append('Kundfaktura-PDF hämtade: %d, bifogade: %d, '
                           'utan matchande faktura: %d'
                           % (rep['fetched'], rep['attached'],
                              rep['missing_move']))
                for e in rep['errors'][:10]:
                    log.append('  x %s' % e)

                supplier_invoices = self.provider.fetch_supplier_invoices()
                rep2 = pdf.export_supplier_invoices(
                    self.provider, supplier_invoices,
                    company=self.company_id, dry_run=self.fortnox_dry_run,
                )
                log.append('Leverantörsfaktura-PDF hämtade: %d, bifogade: %d, '
                           'utan bilaga: %d, utan matchande faktura: %d'
                           % (rep2['fetched'], rep2['attached'],
                              rep2['no_attachment'], rep2['missing_move']))
                for e in rep2['errors'][:10]:
                    log.append('  x %s' % e)

        except Exception as e:
            log.append('ERROR: %s' % e)
            _logger.exception('Fortnox import failed')

        return log

    def _import_sie(self):
        """Importera SIE 4 via egen parser (Odoo 18-anpassad).

        Den gamla implementationen anropade ``l10n_se.sie.import``, en modell
        som inte finns — och ``l10n_se_sie`` refererar till ``account.period``
        och ``account.fiscalyear`` som Odoo 18 har slopat. Därför egen väg.
        """
        log = []
        if not self.sie_file:
            return ['FEL: ingen SIE-fil uppladdad.']

        importer = self.env['l10n_se.fortnox.migration.sie.importer']
        report = importer.import_sie(
            base64.b64decode(self.sie_file),
            company=self.company_id,
            options={
                'import_accounts': self.import_chart_of_accounts,
                'import_opening': self.import_opening_balance,
                'import_vouchers': self.import_journal_entries,
                'dry_run': self.fortnox_dry_run,
            },
        )

        self.imported_accounts = len(report['accounts_created'])
        self.imported_entries = report['vouchers_created']

        log.append('Teckenkodning: %s' % report['encoding'])
        log.append('SIE-typ: %s' % report['sie_type'])
        log.append('Företag i filen: %s' % (report['company'] or '-'))
        log.append('Konton i filen: %d' % report['accounts_total'])
        log.append('Konton skapade: %d' % len(report['accounts_created']))
        log.append('Journaler skapade: %d' % len(report['journals_created']))
        log.append('Ingående balans: %d rader' % report['opening_created'])
        log.append('Verifikationer: %d' % report['vouchers_created'])
        if report['vouchers_skipped']:
            log.append('Överhoppade: %d' % report['vouchers_skipped'])
        if report.get('dry_run'):
            log.append('--- FÖRHANDSGRANSKNING, inget skrivet ---')

        if report['problems']:
            log.append('')
            log.append('KONTROLLER:')
            for p in report['problems'][:30]:
                log.append('  ! %s' % p)
        if report['errors']:
            log.append('')
            log.append('FEL:')
            for e in report['errors'][:30]:
                log.append('  x %s' % e)

        self.sie_report = '\n'.join(log)
        return log

    # ------------------------------------------------------------------
    # Import helpers
    # ------------------------------------------------------------------

    def _import_fortnox_accounts(self, accounts):
        """Skapa konton som saknas. Använder resolver för typ-härledning.

        Fortnox returnerar Number/Description/SRU/Type/Active. Vi låter
        resolveraren avgöra account_type ur BAS-intervallet, med Fortnox
        Type som fallback — aldrig gissa på måfå.
        """
        resolver = self.env['l10n_se.fortnox.migration.account.resolver']
        count = 0
        for acct in accounts:
            number = acct.get('Number')
            if number is None:
                continue
            _, created = resolver.resolve_account(
                number,
                name=acct.get('Description'),
                fortnox_type=acct.get('Type'),
                company=self.company_id,
            )
            if created:
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
            }
            partner_model.create(vals)
            count += 1
        return count

    def _import_fortnox_vouchers(self, vouchers):
        """Skapa account.move från Fortnox-verifikationer.

        Tre saker den gamla versionen missade:
        1. Alla verifikationer hamnade i EN general-journal — serietillhörighet
           försvann. Nu skapas/hittas journal per VoucherSeries.
        2. Rader med okänt konto kastades tyst (`continue`) — verifikationen
           blev obalanserad. Nu skapas kontot via resolveraren.
        3. VoucherRows hämtades aldrig — list-endpointen ger bara huvudet.
           Nu hämtas detaljen per verifikation.
        """
        resolver = self.env['l10n_se.fortnox.migration.account.resolver']
        move_model = self.env['account.move'].with_company(self.company_id)
        count = 0
        errors = []

        for voucher in vouchers:
            series = voucher.get('VoucherSeries') or 'MISC'
            number = voucher.get('VoucherNumber')

            journal, _created = resolver.resolve_journal(
                series, company=self.company_id,
            )

            # Hämta raderna — list-endpointen innehåller dem inte
            rows = voucher.get('VoucherRows')
            if not rows and number is not None:
                try:
                    detail = self.provider.fetch_voucher_detail(series, number)
                    rows = detail.get('VoucherRows') or []
                except FortnoxError as e:
                    errors.append('Verifikation %s/%s: %s' % (series, number, e))
                    continue

            lines = []
            for row in rows or []:
                account, _ = resolver.resolve_account(
                    row.get('Account'),
                    company=self.company_id,
                )
                if not account:
                    continue
                lines.append((0, 0, {
                    'account_id': account.id,
                    'debit': float(row.get('Debit') or 0),
                    'credit': float(row.get('Credit') or 0),
                    'name': row.get('Description') or '',
                }))

            if not lines:
                continue

            # Kontrollera balans innan postning — en obalanserad verifikation
            # ska stoppas, inte tystas
            total_debit = sum(l[2]['debit'] for l in lines)
            total_credit = sum(l[2]['credit'] for l in lines)
            if abs(total_debit - total_credit) > 0.005:
                errors.append(
                    'Verifikation %s/%s obalanserad: debet %.2f != kredit %.2f'
                    % (series, number, total_debit, total_credit)
                )
                continue

            move = move_model.create({
                'journal_id': journal.id,
                'date': voucher.get('TransactionDate') or fields.Date.today(),
                'ref': 'Fortnox %s/%s' % (series, number),
                'line_ids': lines,
            })
            move.action_post()
            count += 1

        if errors:
            _logger.warning('Voucher-import: %d problem', len(errors))
            for e in errors[:20]:
                _logger.warning('  %s', e)
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
