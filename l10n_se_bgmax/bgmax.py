# -*- coding: utf-8 -*-
"""Class to parse camt files."""
##############################################################################
#
#    Copyright (C) 2013-2016 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GMaxNU Affero General Public License as published
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

# git clone -b 8.0 https://github.com/OCA/bank-statement-import.git


import re
from datetime import datetime
from openerp.addons.account_bank_statement_import.parserlib import (
    BankStatement)

import logging
_logger = logging.getLogger(__name__)


class BgMaxParser(object):
    """Parser for BgMax bank statement import files."""

    def __init__(self):
        """Initialize parser - override at least header_regex.
        This in fact uses the ING syntax, override in others."""
        self.bgmax_type = 'General'
        self.header_lines = 0  # Number of lines to skip
        self.header_regex = '^01BGMAX'  # Start of header
        self.footer_regex = '^70'  # Stop processing on seeing this
        self.tag_regex = '^([0-7][0-9])(.*)'  # Start of new tag
        self.current_statement = None
        self.current_transaction = None
        self.statements = []
        self.currency = ''
        self.header_balance = 0.0


    def is_bgmax(self, line):
        """determine if a line is the header of a statement"""
        if not bool(re.match(self.header_regex, line)):
            raise ValueError(
                'File starting with %s does not seem to be a'
                ' valid %s format bank statement.' %
                (line[:12], 'BgMax')
            )

    def parse(self, data):
        """Parse bgmax bank statement file contents."""
        self.is_bgmax(data)
        iterator = data.replace('\r\n', '\n').split('\n').__iter__()
        line = None
        record_line = ''
        try:
            while True:
                if not self.current_statement:
                    self.handle_header(line, iterator)
                line = iterator.next()
                if not self.is_tag(line) and not self.is_footer(line):
                    record_line += line
                    continue
                if record_line:
                    self.handle_record(record_line)
                if self.is_footer(line):
                    self.handle_footer(line, iterator)
                    record_line = ''
                    continue
                record_line = line
        except StopIteration:
            pass
        if self.current_statement:
            if record_line:
                self.handle_record(record_line)
                record_line = ''
            self.statements.append(self.current_statement)
            self.current_statement = None
        return self.statements

    def is_footer(self, line):
        """determine if a line is the footer of a statement"""
        return line and bool(re.match(self.footer_regex, line))

    def is_tag(self, line):
        """determine if a line has a tag"""
        return line and bool(re.match(self.tag_regex, line))

    def handle_header(self, dummy_line, iterator):
        """skip header lines, create current statement"""
        for dummy_i in range(self.header_lines):
            iterator.next()
        self.current_statement = BankStatement()

    def handle_footer(self, dummy_line, dummy_iterator):
        """add current statement to list, reset state"""
        self.statements.append(self.current_statement)
        self.current_statement = None

    def handle_record(self, line):
        """find a function to handle the record represented by line"""
        tag_match = re.match(self.tag_regex, line)
        tag = tag_match.group(1)
        #raise Warning(tag)
        _logger.error('got this tk%s' % tag)
        if not hasattr(self, 'handle_tk%s' % re.match(self.tag_regex, line).group(1)):
            _logger.error('Unknown tk%s', re.match(self.tag_regex, line).group(1))
            _logger.error(line)
            return
        handler = getattr(self, 'handle_tk%s' % re.match(self.tag_regex, line).group(1))
        handler(line)

    def handle_tag_20(self, data):
        """Contains unique ? message ID"""
        pass

    def handle_tag_25(self, data):
        """Handle tag 25: local bank account information."""
        data = data.replace('EUR', '').replace('.', '').strip()
        self.current_statement.local_account = data

    def handle_tag_28C(self, data):
        """Sequence number within batch - normally only zeroes."""
        pass

    def handle_tag_60F(self, data):
        """get start balance and currency"""
        # For the moment only first 60F record
        # The alternative would be to split the file and start a new
        # statement for each 20: tag encountered.
        stmt = self.current_statement
        if not stmt.local_currency:
            stmt.local_currency = data[7:10]
            stmt.start_balance = str2amount(data[0], data[10:])

    def handle_tag_61(self, data):
        """get transaction values"""
        transaction = self.current_statement.create_transaction()
        self.current_transaction = transaction
        transaction.execution_date = datetime.strptime(data[:6], '%y%m%d')
        transaction.value_date = datetime.strptime(data[:6], '%y%m%d')
        #  ...and the rest already is highly bank dependent

    def handle_tag_62F(self, data):
        """Get ending balance, statement date and id.

        We use the date on the last 62F tag as statement date, as the date
        on the 60F record (previous end balance) might contain a date in
        a previous period.

        We generate the statement.id from the local_account and the end-date,
        this should normally be unique, provided there is a maximum of
        one statement per day.

        Depending on the bank, there might be multiple 62F tags in the import
        file. The last one counts.
        """
        stmt = self.current_statement
        stmt.end_balance = str2amount(data[0], data[10:])
        stmt.date = datetime.strptime(data[1:7], '%y%m%d')
        # Only replace logically empty (only whitespace or zeroes) id's:
        # But do replace statement_id's added before (therefore starting
        # with local_account), because we need the date on the last 62F
        # record.
        test_empty_id = re.sub(r'[\s0]', '', stmt.statement_id)
        if ((not test_empty_id) or
                (stmt.statement_id.startswith(stmt.local_account))):
            stmt.statement_id = '%s-%s' % (
                stmt.local_account,
                stmt.date.strftime('%Y-%m-%d'),
            )
    def handle_tk01(self, data):
        """header"""
        self.current_statement = BankStatement()
        
    def handle_tk05(self, data):
        """öppningspost"""
        self.currency = data[22:25]
        self.header_balance = float(data[3:20])
        _logger.error('balance %s currency %s' % (self.header_balance,self.currency))
        
        pass
    def handle_tk15(self, data):
        """insättning"""
        stmt = self.current_statement
        stmt.end_balance = str2amount(data[0], data[10:])
        stmt.date = datetime.strptime(data[1:7], '%y%m%d')
        
    def handle_tk20(self, data):
        """betalning/avdragspost"""
        _logger.error('betalning %s ' % self.current_statement)
        transaction = self.current_statement.create_transaction()
        _logger.error('transaction I %s ' % transaction)
        #{'unique_import_id': '0001', 'name': False, 'partner_name': False, 'amount': 0.0, 'account_number': False, 'date': False, 'ref': False}
        self.current_transaction = transaction
        
        transaction.execution_date = datetime.strptime(data[:6], '%y%m%d')
        transaction.value_date = datetime.strptime(data[:6], '%y%m%d')
        transaction.name = data[12:32]
        _logger.error('transaction %s ' % transaction)
    def handle_tk21(self, data):
        """betalning/avdragspost"""
        pass
    def handle_tk22(self, data):
        """extra referensnummer"""
        pass
    def handle_tk23(self, data):
        """extra referensnummer"""
        pass
    def handle_tk25(self, data):
        """informationspost"""
        pass
    def handle_tk26(self, data):
        """namnpost"""
        pass
    def handle_tk27(self, data):
        """adresspost 1"""
        pass
    def handle_tk28(self, data):
        """adresspost 2"""
        pass
    def handle_tk29(self, data):
        """organisationsnummer"""
        pass
    def handle_tk70(self, data):
        """slutpost"""
        pass

