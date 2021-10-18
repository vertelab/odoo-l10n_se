# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2021 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from openerp import models, fields, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
import base64
import csv
from openerp.addons.account_bank_statement_import.parserlib import BankStatement
import hashlib
from io import BytesIO
import unicodedata
import logging
_logger = logging.getLogger(__name__)

    

class StripePaymentsReport(object):
    """Parser for Stripe Kontohändelser import files."""

    def __init__(self, data_file, filename):
        self.filename = filename
        if not self.filename.lower().endswith(('.csv', '.txt')):
            raise ValueError('Incorrect file format, use csv.')
            
        self.rows = []
        csv_rows = [row for row in csv.reader(data_file.splitlines(), delimiter=',')]
        self.header = csv_rows[0]
        
        if not (self.header[0] == 'id' and self.header[1] == 'Description' and self.header[2] == 'Seller Message'):
            raise ValueError(u'Incorrect file header.')

        #Remove Header from rows
        del csv_rows[0]
        
        for r in csv_rows:
            self.rows.append(r)
        self.statements = []



    def parse(self):
        """Parse stripe transaktionsrapport bank statement file contents type 1."""
        self.account_currency = self.rows[1][6]
        self.name = 'Stripe'
        self.account_number = ''
        self.current_statement = BankStatement()
        self.current_statement.date = fields.Date.today()
        self.current_statement.local_currency = self.account_currency or 'SEK'
        self.current_statement.local_account = self.account_number
        self.current_statement.statement_id = 'Stripe %s - %s' % (self.rows[0][3],
                                                           self.rows[-1][3])
        self.current_statement.start_balance = 0.0
        for t in self.rows:
            transaction = self.current_statement.create_transaction()
            try:
                if not t[4]:
                    t[4] = 0.0
                if not t[5]:
                    t[5] = 0.0
                if not isinstance(t[4], float):
                    t[4] = float(t[4].replace(",", "."))
                if not isinstance(t[5], float):
                    t[5] = float(t[5].replace(",", "."))
                transaction.transferred_amount = float(t[4]) - float(t[5])
                transaction.original_amount = float(t[4]) - float(t[5])
                self.current_statement.end_balance += float(t[4]) - float(t[5])
                transaction.eref = t[1]
                transaction.name = '%s,%s' % (t[16], t[1].strip())
                transaction.value_date = t[3]
                transaction.unique_import_id = t[0]
            except ValueError as e:
                raise ValueError('Invalid values in file', e)

        self.statements.append(self.current_statement)
        return self

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
