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
from odoo.addons.l10n_se_account_bank_statement_import.account_bank_statement_import import BankStatement
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)


class BankStatement(BankStatement):

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
                current_statement.bg_serial_number = avsnitt.footer.get('inslopnummer')
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


class BgMaxGenerator(object):

    def generate(self, record, bg_account, company):
        s = """{open_post}\n""".format(open_post = self.get_open_post(record, bg_account)) # post 11
        # valfri post 12 finns inte här.
        s += """{title_post}\n""".format(title_post = self.get_title_post(record)) # post 13
        for line in record.payment_line_ids:
            s += """{payment_name_post}\n""".format(payment_name_post = self.get_payment_name_post(line)) # post 26
            s += """{payment_address_post}\n""".format(payment_address_post = self.get_payment_address_post(line)) # post 27
            s += """{payment_post}\n""".format(payment_post = self.get_payment_post(line)) # post 14
            # avdragspost 15 finns inte här
            # kreditfakturaspost 16/17 finns inte här
        s += """{end_post}\n""".format(end_post = self.get_end_post(record, bg_account)) # post 29
        f = open('/tmp/BANKGIROINBETALNINGAR%s1.txt' %datetime.today().strftime('%Y-%m-%d'), 'w')
        f.write(s)
        f.close()

    def get_open_post(self, record, bg_account):
        return u"""11{bg_account}{write_date}LEVERANTÖRSBETALNINGAR{payment_date}{reserv1}{currency_code}{reserv2}""".format(
            bg_account = '%010d' % int(bg_account),
            write_date = record.write_date.replace(' ', '').replace('-', '').replace(':', '')[2:],
            payment_date = record.date_generated.replace(' ', '').replace('-', '').replace(':', '')[2:],
            reserv1 = ''.ljust(13),
            currency_code = 'SEK',
            reserv2 = ''.ljust(18)
        )

    def get_title_post(self, record):
        return u"""13{title}{title_amount}{reserv}""".format(
            title = record.name.ljust(25),
            title_amount = 'BELOPP'.rjust(12),
            reserv = ''.ljust(41)
        )

    def get_payment_name_post(self, line):
        return """26{reserv}{receiver_bankgiro} {receiver_name}{extra_info}""".format(
            reserv = '0000',
            receiver_bankgiro = line.bank_line_id.name.replace('L', '').ljust(5),
            receiver_name = line.partner_id.name.ljust(35),
            extra_info = ''.ljust(33)
        )

    def get_payment_address_post(self, line):
        return """27{reserv1}{receiver_bankgiro} {receiver_name}{receiver_zip}{receiver_city}{reserv2}""".format(
            reserv1 = '0000',
            receiver_bankgiro = line.bank_line_id.name.replace('L', '').ljust(5),
            receiver_name = line.partner_id.street.ljust(35) if line.partner_id.street else ''.ljust(35),
            receiver_zip = line.partner_id.zip.replace(' ', '').ljust(5) if line.partner_id.zip else '00000',
            receiver_city = line.partner_id.city.ljust(20) if line.partner_id.city else ''.ljust(20),
            reserv2 = ''.ljust(8)
        )

    def get_payment_post(self, line):
        return """14{receiver_bankgiro} {ocr}{amount}{payment_date}{reserv}{info}""".format(
            # ~ receiver_bankgiro = '%010d' % int(line.partner_bank_id.acc_number.replace('-', '').replace(' ', '')),
            receiver_bankgiro = '%09d' % int(line.bank_line_id.name.replace('L', '')),
            ocr = line.name.ljust(25),
            amount = '%012d' % int(line.amount_currency * 100),
            payment_date = line.date.replace('-', '')[2:],
            reserv = ''.ljust(5),
            info = ''.ljust(20)
        )

    def get_end_post(self, record, bg_account):
        return """29{bg_account}{line_count}{line_total}{negative}{reserv}""".format(
            bg_account = '%010d' % int(bg_account),
            line_count = '%08d' % len(record.payment_line_ids),
            line_total = '%012d' % sum(record.payment_line_ids.mapped('amount_currency')),
            negative = ' ',
            reserv = ''.ljust(47)
        )
