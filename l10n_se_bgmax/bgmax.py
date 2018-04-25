# -*- coding: utf-8 -*-
"""Class to parse camt files."""
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2013-2016 Vertel (<http://vertel.se>).
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
import unicodedata
import re
from datetime import datetime
#~ from odoo.addons.account_bank_statement_import.parserlib import (BankStatement)

import logging
_logger = logging.getLogger(__name__)


class BankTransaction(dict):
    """Single transaction that is part of a bank statement."""

    @property
    def value_date(self):
        """property getter"""
        return self['date']

    @value_date.setter
    def value_date(self, value_date):
        """property setter"""
        self['date'] = value_date

    @property
    def name(self):
        """property getter"""
        return self['name']

    @name.setter
    def name(self, name):
        """property setter"""
        self['name'] = name

    @property
    def transferred_amount(self):
        """property getter"""
        return self['amount']

    @transferred_amount.setter
    def transferred_amount(self, transferred_amount):
        """property setter"""
        self['amount'] = transferred_amount

    @property
    def eref(self):
        """property getter"""
        return self['ref']

    @eref.setter
    def eref(self, eref):
        """property setter"""
        self['ref'] = eref
        if not self.message:
            self.name = eref

    @property
    def message(self):
        """property getter"""
        return self._message

    @message.setter
    def message(self, message):
        """property setter"""
        self._message = message
        self.name = message

    @property
    def remote_owner(self):
        """property getter"""
        return self['partner_name']

    @remote_owner.setter
    def remote_owner(self, remote_owner):
        """property setter"""
        self['partner_name'] = remote_owner
        if not (self.message or self.eref):
            self.name = remote_owner

    @property
    def remote_account(self):
        """property getter"""
        return self['account_number']

    @remote_account.setter
    def remote_account(self, remote_account):
        """property setter"""
        self['account_number'] = remote_account

    @property
    def note(self):
        return self['note']

    @note.setter
    def note(self, note):
        self['note'] = note

    def __init__(self):
        """Define and initialize attributes.

        Not all attributes are already used in the actual import.
        """
        super(BankTransaction, self).__init__()
        self.transfer_type = False  # Action type that initiated this message
        self.execution_date = False  # The posted date of the action
        self.value_date = False  # The value date of the action
        self.remote_account = False  # The account of the other party
        self.remote_currency = False  # The currency used by the other party
        self.exchange_rate = 0.0
        # The exchange rate used for conversion of local_currency and
        # remote_currency
        self.transferred_amount = 0.0  # actual amount transferred
        self.name = ''
        self._message = False  # message from the remote party
        self.eref = False  # end to end reference for transactions
        self.remote_owner = False  # name of the other party
        self.remote_owner_address = []  # other parties address lines
        self.remote_owner_city = False  # other parties city name
        self.remote_owner_postalcode = False  # other parties zip code
        self.remote_owner_country_code = False  # other parties country code
        self.remote_bank_bic = False  # bic of other party's bank
        self.provision_costs = False  # costs charged by bank for transaction
        self.provision_costs_currency = False
        self.provision_costs_description = False
        self.error_message = False  # error message for interaction with user
        self.storno_retry = False
        # If True, make cancelled debit eligible for a next direct debit run
        self.data = ''  # Raw data from which the transaction has been parsed


class BankStatement(dict):
    """A bank statement groups data about several bank transactions."""

    @property
    def statement_id(self):
        """property getter"""
        return self['name']

    def _set_transaction_ids(self):
        """Set transaction ids to statement_id with sequence-number."""
        subno = 0
        for transaction in self['transactions']:
            subno += 1
            transaction['unique_import_id'] = (
                self.statement_id + str(subno).zfill(4))

    @statement_id.setter
    def statement_id(self, statement_id):
        """property setter"""
        self['name'] = statement_id
        self._set_transaction_ids()

    @property
    def local_account(self):
        """property getter"""
        return self['account_number']

    @local_account.setter
    def local_account(self, local_account):
        """property setter"""
        self['account_number'] = local_account

    @property
    def local_currency(self):
        """property getter"""
        return self['currency_code']

    @local_currency.setter
    def local_currency(self, local_currency):
        """property setter"""
        self['currency_code'] = local_currency

    @property
    def start_balance(self):
        """property getter"""
        return self['balance_start']

    @start_balance.setter
    def start_balance(self, start_balance):
        """property setter"""
        self['balance_start'] = start_balance

    @property
    def end_balance(self):
        """property getter"""
        return self['balance_end']

    @end_balance.setter
    def end_balance(self, end_balance):
        """property setter"""
        self['balance_end'] = end_balance
        self['balance_end_real'] = end_balance

    @property
    def date(self):
        """property getter"""
        return self['date']

    @date.setter
    def date(self, date):
        """property setter"""
        self['date'] = date

    def create_transaction(self):
        """Create and append transaction.

        This should only be called after statement_id has been set, because
        statement_id will become part of the unique transaction_id.
        """
        transaction = BankTransaction()
        self['transactions'].append(transaction)
        # Fill default id, but might be overruled
        transaction['unique_import_id'] = (
            self.statement_id + str(len(self['transactions'])).zfill(4))
        return transaction

    @property
    def is_bg(self):
        """property getter"""
        return self['is_bg']

    @is_bg.setter
    def is_bg(self, is_bg):
        """property setter"""
        self['is_bg'] = is_bg

    @property
    def account_no(self):
        """property getter"""
        return self['account_no']

    @account_no.setter
    def account_no(self, account_no):
        """property setter"""
        self['account_no'] = account_no

    def __init__(self):
        super(BankStatement, self).__init__()
        self['transactions'] = []
        self.statement_id = ''
        self.local_account = ''
        self.local_currency = ''
        self.date = ''
        self.start_balance = 0.0
        self.end_balance = 0.0
        self.is_bg = True
        self.account_no = None


class avsnitt(object):
    def __init__(self,rec):
        self.header = rec
        self.footer = {}
        self.ins = []
        self.bet = []
        self.message = []
        self.type = ''
        self.current_type = ''

    def add(self,rec):
        self.type = rec['type']
        if rec['type'] == '20':
            self.current_type = 'ins'
            self.type = '20'
            self.ins.append(rec)
        elif rec['type'] == '21':
            self.current_type = 'bet'
            self.type = '21'
            self.bet.append(rec)
        #~ elif self.type == '20':
            #~ for r in rec.keys():
                #~ self.bet[-1][r] = rec[r].strip()
        #~ elif self.type == '21':
            #~ for r in rec.keys():
                #~ self.ins[-1][r] = rec[r].strip()
        elif self.type == '25':
            if self.current_type == 'ins':
                if not self.ins[-1].get('informationstext'):
                    self.ins[-1]['informationstext'] = []
                self.ins[-1]['informationstext'].append(rec['informationstext'].strip())
            if self.current_type == 'bet':
                if not self.bet[-1].get('informationstext'):
                    self.bet[-1]['informationstext'] = []
                self.bet[-1]['informationstext'].append(rec['informationstext'].strip())
        elif self.type == '26':
            if self.current_type == 'ins':
                self.ins[-1]['betalarens_namn'] = rec['betalarens_namn']
                self.ins[-1]['extra_namn'] = rec['extra_namn']
            if self.current_type == 'bet':
                self.bet[-1]['betalarens_namn'] = rec['betalarens_namn']
                self.bet[-1]['extra_namn'] = rec['extra_namn']
        elif self.type == '27':
            if self.current_type == 'ins':
                self.ins[-1]['betalarens_adress'] = rec['betalarens_adress']
                self.ins[-1]['betalarens_postnr'] = rec['betalarens_postnr']
            if self.current_type == 'bet':
                self.bet[-1]['betalarens_adress'] = rec['betalarens_adress']
                self.bet[-1]['betalarens_postnr'] = rec['betalarens_postnr']
        elif self.type == '28':
            if self.current_type == 'ins':
                self.ins[-1]['betalarens_ort'] = rec['betalarens_ort']
                self.ins[-1]['betalarens_land'] = rec['betalarens_land']
                self.ins[-1]['betalarens_landkod'] = rec['betalarens_landkod']
            if self.current_type == 'bet':
                self.bet[-1]['betalarens_ort'] = rec['betalarens_ort']
                self.bet[-1]['betalarens_land'] = rec['betalarens_land']
                self.bet[-1]['betalarens_landkod'] = rec['betalarens_landkod']
        elif self.type == '29':
            if self.current_type == 'ins':
                self.ins[-1]['organisationsnummer'] = rec['organisationsnummer']
            if self.current_type == 'bet':
                self.bet[-1]['organisationsnummer'] = rec['organisationsnummer']

    def check_insbelopp(self):
        #print "summa",sum([float(b['betbelopp'])/100 for b in self.ins])
        #print "insbel",float(self.footer['insbelopp']) / 100
        if not (int(self.footer['insbelopp'])) == sum([int(b['betbelopp']) for b in self.ins])-sum([int(b['betbelopp']) for b in self.bet]):
            #_logger.error('BgMax check_insbelopp %s != %s' % (int(self.footer['insbelopp']),sum([int(b['betbelopp']) for b in self.ins])))
            str = 'betalare:belopp\n'
            for rec in self.ins:
                str += '%s:%s\n' % (rec['betalarens_namn'],float(rec['betbelopp'])/100.0)
            _logger.error('record\n%s\n%s' % (str,'BgMax check_antal_bet %s != %s' % (len(self.ins)+len(self.bet),int(self.footer['antal_bet']))))
            _logger.error('footer %s' % self.footer)
            raise ValueError('BgMax check_insbelopp %s != %s' % (int(self.footer['insbelopp']),sum([int(b['betbelopp']) for b in self.ins])))
        return (int(self.footer['insbelopp']) == sum([int(b['betbelopp']) for b in self.ins])-sum([int(b['betbelopp']) for b in self.bet]))
    def check_antal_bet(self):
        #print "antal",len(self.ins)
        #print "antal_bet",int(self.footer['antal_bet'])
        if not (len(self.ins)+len(self.bet)) == int(self.footer['antal_bet']):
            #~ _logger.error('BgMax check_antal_bet %s != %s' % (len(self.ins),int(self.footer['antal_bet'])))
            raise ValueError('BgMax check_antal_bet %s != %s' % (len(self.ins)+len(self.bet),int(self.footer['antal_bet'])))
        return (len(self.ins)+len(self.bet)) == int(self.footer['antal_bet'])
    def __str__(self):
        return str({
            'type': self.type,
            'header': self.header,
            'footer': self.footer,
            'ins': self.ins,
            'bet': self.bet,
        })


class BgMaxRowParser(object):
    """Parser for BgMax bank statement import files lines."""

    layout = {
            '01': [ # Start post
                ('layoutnamn',3,22),
                ('version',23,24),
                ('skrivdag',25,44),
                ('testmarkering',45,45),
                ('reserv',46,80),
            ],
            '05': [ # Record start
                ('mottagarbankgiro',3,12),
                ('mottagarplusgiro',13,22),
                ('valuta',46,50),
            ],
            '15': [ # Record end / insättning
                ('mottagarbankkonto',3,37),
                ('betalningsdag',38,45),
                ('inslopnummer',46,50),
                ('insbelopp',51,68),
                ('valuta',69,71),
                ('antal_bet',72,79),
                ('typ_av_ins',80,80),
            ],
            '20': [ # betalning
                ('bankgiro',3,12),
                ('referens',13,37),
                ('betbelopp',38,55),
                ('referenskod',56,56),
                ('betalningskanalkod',57,57),
                ('BGC-nummer',58,69),
                ('avibildmarkering',70,70),
                ('reserv',71,80),
            ],
            '21': [ # avdrag
                ('bankgiro',3,12),
                ('referens',13,37),
                ('betbelopp',38,55),
                ('referenskod',56,56),
                ('betalningskanalkod',57,57),
                ('BGC-nummer',58,69),
                ('avibildmarkering',70,70),
                ('avdragskod',71,71),
            ],
            '22': [
                ('22bankgiro',3,12),
                ('22referens',13,37),
                ('22betbelopp',38,55),
                ('22referenskod',56,56),
                ('22betalningskanalkod',57,57),
                ('22BGC-nummer',58,69),
                ('22avibildmarkering',70,70),
                ('22reserv',71,80),
            ],
            '23': [
                ('23bankgiro',3,12),
                ('23referens',13,37),
                ('23betbelopp',38,55),
                ('23referenskod',56,56),
                ('23betalningskanalkod',57,57),
                ('23BGC-nummer',58,69),
                ('23avibildmarkering',70,70),
                ('reserv',71,80),
            ],
            '25': [
                ('informationstext',3,52),
                ('reserv',53,80),
            ],
            '26': [
                ('betalarens_namn',3,37),
                ('extra_namn',38,72),
                ('reserv',73,80),
            ],
            '27': [
                ('betalarens_adress',3,37),
                ('betalarens_postnr',38,46),
                ('reserv',47,80),
            ],
            '28': [
                ('betalarens_ort',3,37),
                ('betalarens_land',38,72),
                ('betalarens_landkod',73,74),
                ('reserv',75,80),
            ],
            '29': [
                ('organisationsnummer',3,14),
                ('reserv',15,80),
            ],
            '70': [
                ('antal_betposter',3,10),
                ('antal_avdrag',11,18),
                ('antal_ref',19,26),
                ('antal_ins',27,34),
                ('reserv',35,80),
            ],

        }

    def parse_row(self,row):
        record = {'type': row[0:2]}
        for name,start,stop in self.layout[record['type']]:
            record[name] = row[start-1:stop]
        #_logger.warning('parse_row %s' % record)
        return record


class BgMaxIterator(BgMaxRowParser):
    def __init__(self, data):
        self.row = -1
        #~ self.data = unicode(data,'iso8859-1').encode('utf-8').splitlines()
        self.data = unicode(data,'iso8859-1').splitlines()
        self.rows = len(self.data)
        self.header = {}
        self.footer = {}
        self.avsnitt = []

    def __iter__(self):
        return self

    def next(self):
        if self.row > self.rows:
            raise StopIteration
        rec = self.next_rec()
        if rec['type'] == '01':
            self.header = rec
            rec = self.next_rec()
        if rec['type'] == '70':
            self.footer = rec
            raise StopIteration()
        if rec['type'] == '05':
            self.avsnitt.append(avsnitt(rec))
            rec = self.next_rec()
            while rec['type'] in ['20','21','22','23','25','26','27','28','29']:
                _logger.warn("rec: %s" % rec)
                self.avsnitt[-1].add(rec)
                rec = self.next_rec()
            if rec['type'] == '15':
                self.avsnitt[-1].footer = rec
            return self.avsnitt[-1]
        return rec

    def next_rec(self):
        self.row += 1
        return self.parse_row(self.data[self.row])
    def check_avsnitt(self):
        ok = True
        for a in self.avsnitt:
            if not (a.check_insbelopp() and a.check_antal_bet()):
                _logger.error('BGMax check_avsnitt insbelopp %s antal %s' % (a.check_insbelopp() , a.check_antal_bet()))
                ok = False
        #~ raise Warning(self.footer,[a.ins + a.bet for a in self.avsnitt])
        return ok
    def check_antal_ins(self):
        #print "antal",len(self.avsnitt)
        #print "antal_ins",int(self.footer['antal_ins'])
        return len(self.avsnitt) == int(self.footer.get('antal_ins',0))
    def check_antal_betposter(self):
        #print "antal",sum([len(a.ins) for a in self.avsnitt])
        #print "antal_betposter",int(self.footer['antal_betposter'])
        if not sum([len(a.bet) for a in self.avsnitt]) == int(self.footer.get('antal_avdrag',0)):
            _logger.error('BgMax antal_betposter %s == %s (%s)' % (sum([len(a.bet) for a in self.avsnitt]),int(self.footer.get('antal_avdrag',0)),self.footer))
        return sum([len(a.bet) for a in self.avsnitt]) == int(self.footer.get('antal_avdrag',0))
    def check(self):
        ok = True
        for c,result in [('avsnitt',self.check_avsnitt()),('antal_avdrag',self.check_antal_betposter()),('check_antal_ins',self.check_antal_ins())]:
            if not result:
                _logger.error('BgMax-file error %s' % c)
                raise ValueError('BgMax file error %s' % c)
                ok = False
        return ok


class BgMaxParser(object):
    """Parser for BgMax bank statement import files."""

    #~ def __init__(self, data):
        #~ self.row = 0
        #~ self.data = unicode(data,'iso8859-1').splitlines()
        #~ self.rows = len(self.data)
        #~ self.header = {}
        #~ self.footer = {}
        #~ self.avsnitt = []
        #~ self.header_regex = '^01BGMAX'  # Start of header

    def is_bgmax(self, line):
        """determine if a line is the header of a statement"""
        if not bool(re.match(self.header_regex, line)):
            raise ValueError(
                'File starting with %s does not seem to be a'
                ' valid %s format bank statement.' %
                (line[:12], 'BgMax')
            )

    def __init__(self):
        """Initialize parser - override at least header_regex.
        This in fact uses the ING syntax, override in others."""
        self.bgmax_type = 'General'
        self.header_regex = '^01BGMAX'  # Start of header
        self.current_statement = None
        self.current_transaction = None
        self.statements = []
        self.currency = ''
        self.balance_start = 0.0
        self.balance_end_real = 0.0
        self.balance_end = 0.0

    def parse(self, data):
        """Parse bgmax bank statement file contents."""
        self.is_bgmax(data)
        iterator = BgMaxIterator(data)
        for avsnitt in iterator:
            current_statement = BankStatement()
            current_statement.local_currency = avsnitt.footer.get('valuta')
            current_statement.start_balance = 0.0
            current_statement.end_balance = 0.0
            current_statement.is_bg = True
            #~ _logger.warn("header: %s" % avsnitt.header)
            #~ _logger.warn("footer: %s" % avsnitt.footer)
            #~ _logger.warn("ins: %s" % avsnitt.ins)
            #~ _logger.warn("bet: %s" % avsnitt.bet)
            #~ _logger.warn("type: %s" % avsnitt.type)

            if not current_statement.local_account:
                current_statement.local_account = str(int(avsnitt.header.get('mottagarplusgiro', '').strip() or avsnitt.header.get('mottagarbankgiro', '').strip()))
                if len(current_statement.local_account) == 8:
                    current_statement.local_account = current_statement.local_account[:4] + '-' + current_statement.local_account[4:]
            #if not self.current_statement.local_currency:
            #    self.current_statement.local_currency = avsnitt.header.get('valuta').strip() or avsnitt.footer.get('valuta').strip()
            if not current_statement.statement_id:
                current_statement.statement_id = '%sBM %s' % (current_statement.local_account.replace('-', ''), avsnitt.footer.get('inslopnummer'))
            current_statement.account_no = avsnitt.footer.get('mottagarbankkonto').lstrip('0')

            for ins in avsnitt.ins:
                transaction = current_statement.create_transaction()
                #~ if int(ins.get('bankgiro', 0)):
                    #~ transaction.remote_account = str(int(ins.get('bankgiro', 0)))
                transaction.transferred_amount = float(ins.get('betbelopp', 0)) / 100
                current_statement.end_balance += transaction.transferred_amount

                date = avsnitt.footer.get('betalningsdag') or ''
                if date:
                    date = date[:4] + '-' + date[4:6] + '-' + date[6:]
                    current_statement.date = date
                    transaction.value_date = date
                transaction.remote_account = ins.get('bankgiro', '').strip().lstrip('0')
                if len(transaction.remote_account) == 8:
                    transaction.remote_account = transaction.remote_account[:4] + '-' + transaction.remote_account[4:]
                if ins.get('organisationsnummer'):
                    transaction.remote_owner = ins.get('organisationsnummer').strip()
                else:
                    transaction.remote_owner = ins.get('betalarens_namn', '').strip()
                #~ transaction.message
                #~ transaction.remote_owner
                #~ transaction.name
                #~ transaction.note
                #~ transaction.value_date

                transaction.message = ins.get('betalarens_namn', '')
                transaction.eref = ins.get('referens') or ins.get('BGC-nummer')
                transaction.note = '\n'.join(ins.get('informationstext',[]))
                if ins.get('betalarens_adress'):
                    transaction.note += ' %s, %s %s %s' % (ins.get('betalarens_adress'),ins.get('betalarens_postnr'),ins.get('betalarens_ort'),ins.get('betalarens_land'))
                if ins.get('organisationsnummer'):
                    transaction.note += ' %s ' % ins.get('organisationsnummer')
                if ins.get('BGC-nummer'):
                    transaction.note += ' BGC %s ' % ins.get('BGC-nummer')
                if transaction.remote_account:
                    transaction.note += ' bg %s ' % transaction.remote_account

            for bet in avsnitt.bet:
                transaction = current_statement.create_transaction()
                #~ if int(ins.get('bankgiro', 0)):
                    #~ transaction.remote_account = str(int(ins.get('bankgiro', 0)))
                transaction.transferred_amount = float(bet.get('betbelopp', 0)) / 100.0 * -1
                current_statement.end_balance += transaction.transferred_amount

                date = avsnitt.footer.get('betalningsdag') or ''
                if date:
                    date = date[:4] + '-' + date[4:6] + '-' + date[6:]
                    current_statement.date = date
                    transaction.value_date = date
                transaction.remote_account = bet.get('bankgiro', '').strip().lstrip('0')
                if len(transaction.remote_account) == 8:
                    transaction.remote_account = transaction.remote_account[:4] + '-' + transaction.remote_account[4:]
                if bet.get('organisationsnummer'):
                    transaction.remote_owner = bet.get('organisationsnummer','').strip()
                else:
                    transaction.remote_owner = bet.get('betalarens_namn', '').strip()
                #~ transaction.message
                #~ transaction.remote_owner
                #~ transaction.name
                #~ transaction.note
                #~ transaction.value_date

                transaction.message = bet.get('betalarens_namn', '')
                transaction.eref = bet.get('referens') or bet.get('BGC-nummer')
                transaction.note = '\n'.join(bet.get('informationstext',[]))
                if bet.get('betalarens_adress'):
                    transaction.note += ' %s, %s %s %s' % (bet.get('betalarens_adress'),bet.get('betalarens_postnr'),bet.get('betalarens_ort'),bet.get('betalarens_land'))
                if bet.get('organisationsnummer'):
                    transaction.note += ' %s ' % bet.get('organisationsnummer')
                if bet.get('BGC-nummer'):
                    transaction.note += ' BGC %s ' % bet.get('BGC-nummer')
                if transaction.remote_account:
                    transaction.note += ' bg %s ' % transaction.remote_account
            self.statements.append(current_statement)

        if not iterator.check():
            _logger.error('BgMax-file error')
        #raise Warning(self.statements)
        #_logger.warning('currency_code %s' % self.statements[0].pop('currency_code'))
        #_logger.warning('transactions %s' % self.statements[0]['transactions'])

        #~ return (current_statement.local_currency,current_statement.local_account, self.statements)

        return self.statements
