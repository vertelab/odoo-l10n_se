# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015-2019 Vertel AB <http://vertel.se>
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
from csv import DictReader
import io
import hashlib
import os
import tempfile

from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)

# ~ csvfile = open('bokf_test.skv')
#csvfile = open('testbank.txt')

# ~ reader = csv.DictReader(csvfile)
# ~ _logger.info('reader is working...')

# ~ print reader
# ~ print list(csv.reader(csvfile))



class HandelsbankenTransaktionsrapport(object):
    """Parser for Handelsbanken Transaktions import files (CSV)."""
    
    def __init__(self, data_file):
        #_logger.error('Parser %s' % data_file)
        
        try:
            rows = []
            fp = io.StringIO(data_file.decode("latin-1"))
            fp.seek(0)
            reader = DictReader(fp, delimiter="\t")
            for row in reader:
                rows.append(row)
            fp.close()
            self.data = rows
        except IOError as e:
            _logger.error(u'Could not read CSV file')
            raise ValueError(e)
        # ~ Kontohavare;Kontonr;IBAN;BIC;Kontoform;Valuta;Kontoförande kontor;Datum intervall;Kontor;Bokföringsdag;Reskontradag;Valutadag;Referens;
        # ~ Insättning/Uttag;Bokfört saldo;Aktuellt saldo;Valutadagssaldo;Referens Swish;Avsändar-id Swish;

        _logger.warning(self.data[0])
        if not ('BIC' in self.data[0] and 'Kontoform' in self.data[0] and 'IBAN' in self.data[0]):
            raise ValueError('This is not a Handelsbanken Transaktionsrapport')
        # ~ _logger.warn(self.data[0])
        self.nrows = len(self.data)
        self.account = account()
        self.account.routing_number = self.data[0]['Kontonr']
        self.account.balance_start = float(self.data[0]['Aktuellt saldo'].replace(",","."))
        self.account.balance_end = 0
        self.account.currency = self.data[0]['Valuta']
        self.account.number = self.data[0]['Kontonr']
        self.account.pref = self.data[0]['Kontonr']
        self.account.date = fields.Date.today()
        self.statements = []

    def parse(self):
        if not ('BIC' in self.data[0] and 'HANDSESS' in self.data[0]['BIC']):
            raise ValueError('This is not a Handelsbanken Transaktionsrapport')
        for index, row in enumerate(self.data):
            self.statements.append(row)
        return self #HandelsbankenIterator(self.data, header)
        
        
class account(object):
    pass

class HandelsbankenIterator(object):
    def __init__(self, data, header):
        # Set to minus 1 as we have no header.
        self.row = -1
        self.data = data
        self.rows = len(data) - 1
        self.header = header
        self.account = account()
        self.account.routing_number = self.data[0]['Kontonr']
        self.account.balance_start = 0
        self.account.balance_end = 0
        self.account.currency = self.data[0]['Valuta']
        self.account.number = self.data[0]['Kontonr']
        self.account.name = self.data[0]['Kontonr']
        
    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data[self.row + 1]
        self.row += 1
        return {n: r[n] for n in self.header}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
