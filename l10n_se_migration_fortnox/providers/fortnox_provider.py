# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<http://vertel.se>).
#
##############################################################################
"""Fortnox REST API v3 client.

Verifierat mot Fortnox officiella OpenAPI-spec (api.fortnox.se/apidocs).

Auth: Fortnox använder INTE ``Authorization: Bearer``. Rätt är två headers:
    Access-Token: <token>
    Client-Secret: <secret>

Rate limit: 25 req / 5 s per access-token. Vi throttlar och backoffar på 429.
"""

import logging
import time

import requests

_logger = logging.getLogger(__name__)

BASE_URL = 'https://api.fortnox.se/3'

# Fortnox tillåter max 500 poster per sida.
PAGE_LIMIT = 500
# 25 req / 5 s => 0.2 s mellan anrop. Vi lägger marginal.
MIN_INTERVAL = 0.22


class FortnoxError(Exception):
    """Fel från Fortnox API."""


class FortnoxProvider:
    """Klient för Fortnox API v3.

    Hanterar autentisering, paginering, throttling och rå filhämtning.
    """

    def __init__(self, access_token, client_secret):
        if not access_token:
            raise FortnoxError('Access token saknas.')
        if not client_secret:
            raise FortnoxError('Client secret saknas.')
        self.access_token = access_token
        self.client_secret = client_secret
        self._last_call = 0.0
        self.session = self._build_session()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def _build_session(self):
        session = requests.Session()
        session.headers.update({
            'Access-Token': self.access_token,
            'Client-Secret': self.client_secret,
            'Accept': 'application/json',
        })
        return session

    def _throttle(self):
        delta = time.monotonic() - self._last_call
        if delta < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - delta)
        self._last_call = time.monotonic()

    def get(self, path, params=None, raw=False, _retry=0):
        """GET mot Fortnox. Returnerar JSON eller rå bytes."""
        self._throttle()
        url = BASE_URL + path
        headers = {'Accept': '*/*'} if raw else {}

        try:
            resp = self.session.get(url, params=params, headers=headers, timeout=120)
        except requests.RequestException as e:
            raise FortnoxError('Nätverksfel mot %s: %s' % (url, e)) from e

        if resp.status_code == 429 and _retry < 5:
            wait = 2 ** _retry
            _logger.warning('Fortnox 429 — backoff %ss', wait)
            time.sleep(wait)
            return self.get(path, params, raw, _retry + 1)

        if resp.status_code == 401:
            raise FortnoxError(
                'Fortnox nekade åtkomst (401). Kontrollera Access-Token och '
                'Client-Secret — token gäller 1 timme.'
            )
        if resp.status_code == 403:
            raise FortnoxError(
                'Fortnox nekade behörighet (403). Saknar integrationen scope '
                'för %s?' % path
            )
        if resp.status_code == 404:
            raise FortnoxError('Fortnox: %s finns inte (404).' % path)
        if not resp.ok:
            raise FortnoxError(
                'Fortnox %s %s: %s' % (resp.status_code, path, resp.text[:400])
            )

        return resp.content if raw else resp.json()

    def paginate(self, path, key, params=None):
        """Iterera alla sidor. Fortnox: page/limit + MetaInformation.@TotalPages."""
        page = 1
        while True:
            p = dict(params or {})
            p.update({'page': page, 'limit': PAGE_LIMIT})
            data = self.get(path, p)
            rows = data.get(key) or []
            for row in rows:
                yield row

            meta = data.get('MetaInformation') or {}
            total_pages = meta.get('@TotalPages')
            if not rows:
                break
            if total_pages is not None:
                if page >= int(total_pages):
                    break
            elif len(rows) < PAGE_LIMIT:
                # Ingen meta — fall tillbaka på sidlängd
                break
            page += 1

    # ------------------------------------------------------------------
    # Enskilda resurser
    # ------------------------------------------------------------------

    def test_connection(self):
        data = self.get('/companyinformation')
        return (data.get('CompanyInformation') or {})

    def fetch_company_information(self):
        return self.test_connection()

    def fetch_accounts(self):
        """Kontoplan. Fortnox: Number, Description, SRU, Active, Year."""
        return list(self.paginate('/accounts', 'Accounts'))

    def fetch_customers(self):
        return list(self.paginate('/customers', 'Customers'))

    def fetch_suppliers(self):
        return list(self.paginate('/suppliers', 'Suppliers'))

    def fetch_articles(self):
        return list(self.paginate('/articles', 'Articles'))

    def fetch_financial_years(self):
        return list(self.paginate('/financialyears', 'FinancialYears'))

    def fetch_voucher_series(self):
        return list(self.paginate('/voucherseries', 'VoucherSeries'))

    def fetch_cost_centers(self):
        return list(self.paginate('/costcenters', 'CostCenters'))

    def fetch_projects(self):
        return list(self.paginate('/projects', 'Projects'))

    def fetch_invoices(self, date_from=None, date_to=None, lastmodified=None):
        params = {}
        if lastmodified:
            params['lastmodified'] = lastmodified
        elif date_from:
            params['fromdate'] = date_from
            if date_to:
                params['todate'] = date_to
        return list(self.paginate('/invoices', 'Invoices', params))

    def fetch_supplier_invoices(self, date_from=None, date_to=None,
                                lastmodified=None):
        params = {}
        if lastmodified:
            params['lastmodified'] = lastmodified
        elif date_from:
            params['fromdate'] = date_from
            if date_to:
                params['todate'] = date_to
        return list(self.paginate('/supplierinvoices', 'SupplierInvoices', params))

    def fetch_vouchers(self, financial_year=None, date_from=None, date_to=None):
        """Verifikationer.

        OBS: Fortnox filtrerar på ``financialyear`` (räkenskapsårets *id*,
        inte årtal) eller på datumintervall. Tidigare implementation tog emot
        financial_year men ignorerade den — det är rättat här.
        """
        params = {}
        if financial_year:
            params['financialyear'] = financial_year
        elif date_from:
            params['fromdate'] = date_from
            if date_to:
                params['todate'] = date_to
        return list(self.paginate('/vouchers', 'Vouchers', params))

    def fetch_voucher_detail(self, series, number):
        """Enskild verifikation med VoucherRows."""
        data = self.get('/vouchers/%s/%s' % (series, number))
        return data.get('Voucher') or {}

    def fetch_invoice_payments(self):
        return list(self.paginate('/invoicepayments', 'InvoicePayments'))

    def fetch_supplier_invoice_payments(self):
        return list(self.paginate('/supplierinvoicepayments',
                                  'SupplierInvoicePayments'))

    def fetch_invoice_accruals(self):
        return list(self.paginate('/invoiceaccruals', 'InvoiceAccruals'))

    def fetch_supplier_invoice_accruals(self):
        return list(self.paginate('/supplierinvoiceaccruals',
                                  'SupplierInvoiceAccruals'))

    # ------------------------------------------------------------------
    # SIE — helhetskopia per räkenskapsår
    # ------------------------------------------------------------------

    def fetch_sie(self, sie_type=4, financial_year=None,
                  date_from=None, date_to=None):
        """Hämta SIE-fil som rå bytes.

        ``sie_type`` 4 = full bokföring (kontoplan + IB/UB + verifikationer
        + dimensioner). Fortnox dokumenterar bara typ 4 i sitt exempel.
        """
        params = {}
        if financial_year:
            params['financialYear'] = financial_year
        if date_from:
            params['fromdate'] = date_from
        if date_to:
            params['todate'] = date_to
        return self.get('/sie/%s' % sie_type, params, raw=True)

    # ------------------------------------------------------------------
    # Fakturabilder (PDF)
    # ------------------------------------------------------------------

    def fetch_invoice_pdf(self, document_number, preview=True):
        """Kundfaktura som PDF.

        ``preview`` sätter INTE Sent=TRUE på fakturan — använd det för export.
        ``print`` markerar fakturan som skickad i Fortnox.
        """
        endpoint = 'preview' if preview else 'print'
        return self.get('/invoices/%s/%s' % (document_number, endpoint), raw=True)

    def fetch_supplier_invoice_pdf(self, invoice_number):
        """Leverantörsfakturans original-PDF.

        Fortnox har ingen print-endpoint för leverantörsfakturor. Originalet
        ligger som bilaga: supplierinvoicefileconnections -> /archive?fileid=
        """
        data = self.get('/supplierinvoicefileconnections',
                        {'supplierinvoicenumber': invoice_number})
        conns = data.get('SupplierInvoiceFileConnections') or []
        if not conns:
            return None, None
        file_id = conns[0].get('FileId')
        if not file_id:
            return None, None
        blob = self.get('/archive/%s' % file_id, {'fileid': file_id}, raw=True)
        return blob, conns[0].get('Name')

    def fetch_voucher_attachments(self):
        """Verifikationsbilagor (kvitton)."""
        data = self.get('/voucherfileconnections')
        return data.get('VoucherFileConnections') or []

    def fetch_archive_file(self, file_id):
        return self.get('/archive/%s' % file_id, {'fileid': file_id}, raw=True)
