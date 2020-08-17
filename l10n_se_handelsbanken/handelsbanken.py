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
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)

import csv
import os
import tempfile

# ~ csvfile = open('bokf_test.skv')
#csvfile = open('testbank.txt')

# ~ reader = csv.DictReader(csvfile)
# ~ _logger.info('reader is working...')

# ~ print reader
# ~ print list(csv.reader(csvfile))



class HandelsbankenTransaktionsrapport(object):
    """Parser for Handelsbanken Transaktions import files (CSV)."""
    
    def __init__(self, data_file):
        _logger.error('Parser %s' % data_file)
        
        try:
            rows = []
            fp = tempfile.TemporaryFile()
            fp.write(data_file)
            fp.seek(0)
            reader = csv.DictReader(fp,delimiter=";")
            for row in reader:
                _logger.warn('My row %s' % row)
                rows.append(row)
            fp.close()
            self.data = rows
        except IOError as e:
            _logger.error(u'Could not read CSV file')
            raise ValueError(e)
        _logger.error('%s' % self.data[0].keys())
        # ~ Kontohavare;Kontonr;IBAN;BIC;Kontoform;Valuta;Kontoförande kontor;Datum intervall;Kontor;Bokföringsdag;Reskontradag;Valutadag;Referens;
        # ~ Insättning/Uttag;Bokfört saldo;Aktuellt saldo;Valutadagssaldo;Referens Swish;Avsändar-id Swish;
        
        if not ( 'Valutadag' in self.data[0].keys() and 'Reskontradag' in self.data[0].keys() and 'Kontor' in self.data[0].keys() and 'Datum intervall' in self.data[0].keys()):
            _logger.error( "valuta: %s , Reskonstra %s, Kontor %s , Datum %s %s" % (self.data[0].get('Valutadag') , self.data[0].get('Reskontradag'), self.data[0].get('Kontor'), self.data[0].get('Datum intervall'), self.data[0]) ) 
                        
            _logger.error(u"Row 0 was looking for 'Kontohavare','Kontonr','IBAN','BIC','Kontoform','Valuta,Kontoförande kontor'")
            raise ValueError('This is not a Handelsbanken Transaktionsrapport')

        self.nrows = len(self.data)
        self.header = []
        self.statements = []

    def parse(self):
        """Parse handelsbanken bank statement file contents."""
        if not ( 'Valutadag' in self.data[0].keys() and 'Reskontradag' in self.data[0].keys() and 'Kontor' in self.data[0].keys() and 'Datum intervall' in self.data[0].keys()):
        # ~ if not (self.data[0].get('Valutadag') and self.data[0].get('Reskontradag') and self.data[0].get('Kontor') and self.data[0].get('Datum intervall')):
        # ~ if not (self.data[0].get('Valutadag') ):
            # ~ if not self.data[0].keys() == ['Kontohavare','Kontonr','IBAN','BIC','Kontoform','Valuta','Kontoförande kontor','Datum intervall','Kontor','Bokföringsdag','Reskontradag','Valutadag','Referens','Insättning/Uttag','Bokfört saldo','Aktuellt saldo','Valutadagssaldo','Referens Swish','Avsändar-id Swish']:
            # ~ _logger.error(u"Row 0 was looking for 'Kontohavare','Kontonr','IBAN','BIC','Kontoform','Valuta,Kontoförande kontor'")
            raise ValueError('This is not a Handelsbanken Transaktionsrapport')
       
        header = {
                'Kontohavare': None,
                'Kontonr': None,
                'IBAN': None,
                'BIC': None,
                'Kontoform': None,
                'Valuta': None,
                u'Kontoförande kontor': None,
                'Datum intervall': None,
                'Kontor': None,
                u'Bokföringsdag': 'date',
                'Reskontradag': None,
                'Valutadag': None,
                'Referens': 'memo',
                u'Insättning/Uttag': 'memo',
                u'Bokfört saldo': 'amount',
                'Aktuellt saldo': None,
                'Valutadagssaldo': None,
                'Referens Swish': None,
                u'Avsändar-id Swish': None
            # 'valutadag': 'date',
            # 'referens': 'payee',
            # 'text': 'memo',
            # 'belopp': 'amount',
            # ~ 'Bokföringsdag': 'date',
            # ~ 'Referense': 'payee',
            # ~ 'text': 'memo',
            # ~ 'l10n_se': 'amount',
            #'Valutadag': 'date',
            #'Referens': 'payee',
            #'Insättning/Uttag': 'memo',
            #'Bokfört saldo': 'amount',
            }
             
        #_logger.error('t: %s' % [t.keys() for t in SwedbankIterator(self.data)])
        #raise Warning([n for n in [t.keys() for t in SwedbankIterator(self.data)]])
        #return {header.get(n,n): t[n] for n in [t.keys() for t in SwedbankIterator(self.data)]}
        return HandelsbankenIterator(self.data)
        
        
class account(object):
    pass

# ~ Kontohavare;Kontonr;IBAN;BIC;Kontoform;Valuta;Kontoförande kontor;Datum intervall;Kontor;Bokföringsdag;Reskontradag;
# ~ Valutadag;Referens;Insättning/Uttag;Bokfört saldo;Aktuellt saldo;Valutadagssaldo;Referens Swish;Avsändar-id Swish;

class HandelsbankenIterator(object):
    def __init__(self, data):
        self.row = 0
        self.data = data
        self.rows = len(data) - 2
        self.header = data[0].keys()
        self.account = account()
        self.account.routing_number = self.data[1]['Kontonr']
        self.account.balance_start = self.data[1]['Aktuellt saldo']
        self.account.balance_end = self.data[-1]['Aktuellt saldo']
        self.account.currency = self.data[1]['Valuta']
        self.account.number = self.data[1]['Kontonr']
        self.account.name = self.data[1]['Kontonr']

    def __iter__(self):
        return self

    def next(self):
        if self.row >= self.rows:
            raise StopIteration
        r = self.data[self.row + 2]
        self.row += 1
        return {n: r[n] for n in self.header}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
