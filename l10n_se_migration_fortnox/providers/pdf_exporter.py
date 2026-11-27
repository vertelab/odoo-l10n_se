# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<http://vertel.se>).
#
##############################################################################
"""Ladda ner faktura-PDF:er från Fortnox och bifoga i Odoo.

Kundfakturor: ``/3/invoices/{nr}/preview`` — sätter INTE Sent=TRUE.
Leverantörsfakturor: ingen print-endpoint. Originalet ligger som bilaga:
    /3/supplierinvoicefileconnections?supplierinvoicenumber=...
      -> FileId -> /3/archive/{id}?fileid=...

Bifogas som ``ir.attachment`` på motsvarande ``account.move``.
"""

import base64
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

from .fortnox_provider import FortnoxError

_logger = logging.getLogger(__name__)


class FortnoxPdfExporter(models.AbstractModel):
    _name = 'l10n_se.fortnox.migration.pdf'
    _description = 'Fortnox PDF Exporter'

    # ------------------------------------------------------------------
    # Bifoga
    # ------------------------------------------------------------------

    @api.model
    def _attach(self, move, blob, filename):
        """Bifoga PDF på account.move om den inte redan finns."""
        if not blob or not move:
            return False

        Attachment = self.env['ir.attachment']
        existing = Attachment.search([
            ('res_model', '=', 'account.move'),
            ('res_id', '=', move.id),
            ('name', '=', filename),
        ], limit=1)
        if existing:
            return False

        Attachment.create({
            'name': filename,
            'res_model': 'account.move',
            'res_id': move.id,
            'datas': base64.b64encode(blob),
            'mimetype': 'application/pdf',
        })
        return True

    # ------------------------------------------------------------------
    # Kundfakturor
    # ------------------------------------------------------------------

    @api.model
    def export_customer_invoices(self, provider, invoices, company=None,
                                 dry_run=False):
        """Hämta PDF för kundfakturor och bifoga på matchande move.

        Matchning: Fortnox ``DocumentNumber`` -> ``account.move.ref`` som
        innehåller numret, eller ``name`` om fakturan redan har Fortnox-nummer.
        """
        company = company or self.env.company
        Move = self.env['account.move'].with_company(company)
        report = {'fetched': 0, 'attached': 0, 'missing_move': 0, 'errors': []}

        for inv in invoices:
            number = inv.get('DocumentNumber')
            if number is None:
                continue

            try:
                blob = provider.fetch_invoice_pdf(number, preview=True)
            except FortnoxError as e:
                report['errors'].append('Faktura %s: %s' % (number, e))
                continue

            if not blob:
                report['errors'].append('Faktura %s: tom PDF' % number)
                continue
            report['fetched'] += 1

            if dry_run:
                continue

            move = Move.search([
                ('move_type', '=', 'out_invoice'),
                ('ref', 'ilike', str(number)),
            ], limit=1)
            if not move:
                move = Move.search([
                    ('move_type', '=', 'out_invoice'),
                    ('name', 'ilike', str(number)),
                ], limit=1)

            if not move:
                report['missing_move'] += 1
                continue

            date = inv.get('InvoiceDate') or ''
            filename = 'kundfaktura_%s_%s.pdf' % (number, date)
            if self._attach(move, blob, filename):
                report['attached'] += 1

        return report

    # ------------------------------------------------------------------
    # Leverantörsfakturor
    # ------------------------------------------------------------------

    @api.model
    def export_supplier_invoices(self, provider, invoices, company=None,
                                 dry_run=False):
        """Hämta leverantörsfakturornas original-PDF via bilagekedjan."""
        company = company or self.env.company
        Move = self.env['account.move'].with_company(company)
        report = {'fetched': 0, 'attached': 0, 'missing_move': 0,
                  'no_attachment': 0, 'errors': []}

        for inv in invoices:
            invoice_number = inv.get('InvoiceNumber')
            given_number = inv.get('GivenNumber')
            if not invoice_number:
                continue

            try:
                blob, name = provider.fetch_supplier_invoice_pdf(invoice_number)
            except FortnoxError as e:
                report['errors'].append(
                    'Leverantörsfaktura %s: %s' % (invoice_number, e)
                )
                continue

            if not blob:
                report['no_attachment'] += 1
                continue
            report['fetched'] += 1

            if dry_run:
                continue

            move = Move.search([
                ('move_type', '=', 'in_invoice'),
                ('ref', 'ilike', str(invoice_number)),
            ], limit=1)
            if not move and given_number:
                move = Move.search([
                    ('move_type', '=', 'in_invoice'),
                    ('ref', 'ilike', str(given_number)),
                ], limit=1)

            if not move:
                report['missing_move'] += 1
                continue

            filename = name or 'leverantorsfaktura_%s.pdf' % invoice_number
            if self._attach(move, blob, filename):
                report['attached'] += 1

        return report

    # ------------------------------------------------------------------
    # Verifikationsbilagor
    # ------------------------------------------------------------------

    @api.model
    def export_voucher_attachments(self, provider, company=None,
                                   dry_run=False):
        """Bifoga kvitton på verifikationer."""
        company = company or self.env.company
        Move = self.env['account.move'].with_company(company)
        report = {'fetched': 0, 'attached': 0, 'missing_move': 0,
                  'errors': []}

        try:
            conns = provider.fetch_voucher_attachments()
        except FortnoxError as e:
            report['errors'].append(str(e))
            return report

        for conn in conns:
            file_id = conn.get('FileId')
            series = conn.get('VoucherSeries')
            number = conn.get('VoucherNumber')
            if not file_id:
                continue

            try:
                blob = provider.fetch_archive_file(file_id)
            except FortnoxError as e:
                report['errors'].append('Bilaga %s: %s' % (file_id, e))
                continue

            if not blob:
                continue
            report['fetched'] += 1

            if dry_run:
                continue

            move = Move.search([
                ('ref', 'ilike', '%s/%s' % (series, number)),
            ], limit=1)
            if not move:
                report['missing_move'] += 1
                continue

            filename = conn.get('Name') or 'bilaga_%s.pdf' % file_id
            if self._attach(move, blob, filename):
                report['attached'] += 1

        return report
