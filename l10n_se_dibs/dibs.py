# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2018- Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from odoo import models, fields, api, _
from odoo.http import request
from odoo.exceptions import except_orm, Warning, RedirectWarning
from odoo.addons.l10n_se_account_bank_statement_import.account_bank_statement_import import BankStatement
import datetime

import logging
_logger = logging.getLogger(__name__)

import sys
import tempfile

CURRENCIES = {
    '208': u'Danska Kronor (DKK)',
    '978': u'Euro (EUR)',
    '840': u'US Dollar $ (USD)',
    '826': u'Engelska Pund £ (GBP)',
    '752': u'Svenska Kronor (SEK)',
    '036': u'Australiensiska Dollar (AUD)',
    '124': u'Kanadensiska Dollar (CAD)',
    '352': u'Isländska Kronor (ISK)',
    '392': u'Japanska Yen (JPY)',
    '554': u'New Zealändska Dollar (NZD)',
    '578': u'Norska Kronor (NOK)',
    '756': u'Schweiziska Franc (CHF)',
    '949': u'Turkiska Lire (TRY)',
}


class DibsTransaktionsrapportType(object):
    """Parser for DIBS Kontohändelser import files."""

    def __init__(self, data_file):
        try:
            fp = tempfile.TemporaryFile()
            fp.write(data_file)
            fp.seek(0)
            rows = fp.readlines()
            fp.close()
            self.data = rows
        except IOError as e:
            _logger.error(u'Could not read DIBS file')
            raise ValueError(e)
        if ('Transaktionsrapport' not in self.data[0].split(' ')) or (self.data[4] != 'Transaktionsperiod:\n') or ('Ordernr' not in self.data[8].split(',')):
            _logger.error(u'Row 0 was looking for "Transaktionsrapport", "Transaktionsperiod" and "Ordernr".')
            raise ValueError(u'This is not a DIBS Report')

        self.statements = []

    def parse(self):
        """Parse DIBS transaktionsrapport bank statement file contents."""
        def date_format(date, start_date):
            d = date.strip().replace('\n', '')
            try:
                datetime.datetime.strptime(d, '%d/%m-%Y kl. %H:%M:%S')
                return '%s-%s-%s' %(d[6:10], d[3:5], d[:2])
            except ValueError:
                _logger.error('%s has en error date format' %date)
            d = start_date.replace(' \n', '')
            return '%s-%s-%s' %(d[6:10], d[3:5], d[:2])

        self.account_currency = 'SEK'
        self.account_number = self.data[0][self.data[0].find('(')+1 : self.data[0].find(')')].split(' ')[0]

        self.current_statement = BankStatement()
        self.current_statement.date = fields.Date.today()
        self.current_statement.local_currency = self.account_currency or 'SEK'
        self.current_statement.local_account =  self.account_number
        start_date = self.data[5].split('kl.')[0].split(':')[1].strip()
        self.current_statement.statement_id = 'DIBS %s %s - %s %s' %(self.data[5].split('kl.')[0].split(':')[1].strip(), self.data[5].split('kl.')[1].strip(), self.data[6].split('kl.')[0].split(':')[1].strip(), self.data[6].split('kl.')[1].strip())
        self.current_statement.start_balance = 0.0
        for t in self.data[9:]:
            values = t.split(',')
            curr = CURRENCIES.get(values[3], '')
            currency = curr[curr.find('(')+1 : curr.find(')')].split(' ')[0]
            ordernr = values[0]
            transactionsnr = values[1]
            cardtype = values[5]
            debpoint = date_format(values[6], start_date)
            if currency == 'EUR':
                eur = request.env['res.currency'].search([('name','=', 'EUR')])
                amount = round(float(values[2]) / eur.rate, 2)
                fee_text = values[4]
                fee = round(float(fee_text.replace('??', '0.00')) / eur.rate, 2) # TODO: Unkown fee?
            elif currency == 'USD':
                usd = request.env['res.currency'].search([('name','=', 'USD')])
                amount = round(float(values[2]) / usd.rate, 2)
                fee_text = values[4]
                fee = round(float(fee_text.replace('??', '0.00')) / usd.rate, 2)
            else:
                amount = float(values[2])
                fee_text = values[4]
                fee = float(fee_text.replace('??', '0.00'))
            transaction = self.current_statement.create_transaction()
            transaction.transferred_amount = amount + fee
            self.current_statement.end_balance += amount + fee
            transaction.eref = ordernr
            transaction.name = '%s (%s)' % (ordernr, transactionsnr)
            transaction.note = 'Belopp: %s\nAvgift: %s\nTransaction ID: %s' % (amount, fee_text, transactionsnr)
            transaction.value_date = debpoint
            transaction.unique_import_id = ordernr

        self.statements.append(self.current_statement)
        return self

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
