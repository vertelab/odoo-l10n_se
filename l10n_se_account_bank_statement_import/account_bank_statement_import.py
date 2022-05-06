# -*- coding: utf-8 -*-
"""Class to parse camt files."""
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2018 Vertel (<http://vertel.se>).
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
from odoo import api,models,fields, _
import unicodedata
import re
from datetime import datetime

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
    def original_amount(self):
        """property getter"""
        return self['original_amount']

    @original_amount.setter
    def original_amount(self, original_amount):
        """property setter"""
        self['original_amount'] = original_amount

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
    def pref(self):
        """property getter"""
        return self['payment_ref']

    @pref.setter
    def pref(self, pref):
        """property setter"""
        self['payment_ref'] = pref
        if not self.message:
            self.name = pref

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
    def narration(self):
        return self['narration']

    @narration.setter
    def narration(self, narration):
        self['narration'] = narration

    @property
    def bg_account(self):
        return self['bg_account']

    @bg_account.setter
    def bg_account(self, bg_account):
        self['bg_account'] = bg_account

    @property
    def bg_serial_number(self):
        return self['bg_serial_number']

    @bg_serial_number.setter
    def bg_serial_number(self, bg_serial_number):
        self['bg_serial_number'] = bg_serial_number

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
        self.pref = False # payment reference for odoo 14
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
        self.bg_account = ''
        self.bg_serial_number = ''


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

    @property
    def bg_serial_number(self):
        """property getter"""
        return self['bg_serial_number']

    @date.setter
    def bg_serial_number(self, bg_serial_number):
        """property setter"""
        self['bg_serial_number'] = bg_serial_number

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

    def __init__(self):
        super(BankStatement, self).__init__()
        self['transactions'] = []
        self.statement_id = ''
        self.local_account = ''
        self.local_currency = ''
        self.date = ''
        self.start_balance = 0.0
        self.end_balance = 0.0


class AccountBankStatementImport(models.TransientModel):
    """Extend model account.statment.import."""
    _inherit = 'account.statement.import'

    @api.model
    def _parse_all_files(self, statement_file):
        """Parse one file or multiple files from zip-file.

        Return array of statements for further processing.
        """
        statements = []
        files = [statement_file]
        try:
            with ZipFile(StringIO(statement_file), 'r') as archive:
                files = [
                    archive.read(filename) for filename in archive.namelist()
                    if not filename.endswith('/')
                    ]
        except BadZipfile:
            pass
        # Parse the file(s)
        for import_file in files:
            # The appropriate implementation module(s) returns the statements.
            # Actually we don't care wether all the files have the same
            # format. Although unlikely you might mix mt940 and camt files
            # in one zipfile.
            parse_result = self._parse_file(import_file)
            # Check for old version result, with separate currency and account
            if isinstance(parse_result, tuple) and len(parse_result) == 3:
                (currency_code, account_number, new_statements) = parse_result
                for stmt_vals in new_statements:
                    stmt_vals['currency_code'] = currency_code
                    stmt_vals['account_number'] = account_number
            else:
                new_statements = parse_result
            statements += new_statements
        return statements

    @api.model
    def _create_bank_statements(self, stmts_vals, result):
        ''' Override create method, do auto reconcile after statement created. '''

        for st_vals in stmts_vals:
            for lvals in st_vals["transactions"]:
                if "date" in lvals:
                    date = lvals["date"]
                    try:
                        date = datetime.strptime(date, "%Y-%m-%d")
                    except TypeError:
                        pass 
                    period_id = self.env["account.period"].date2period(date).id
                    lvals["period_id"] = period_id

        for i in range(len(stmts_vals)):
            currency_id = self.env.ref('base.'+stmts_vals[i].pop('currency_code')).id
            # if 'account_number' in stmts_vals[i]:
            #     account_no = stmts_vals[i].pop('account_number')
            #     stmts_vals[i]['account_no'] = account_no
            stmts_vals[i]['currency_id'] = int(currency_id)
        super(AccountBankStatementImport, self)._create_bank_statements(stmts_vals, result)
        statement_ids = result['statement_ids']
        # if len(statement_ids) > 0:
        #     for statement in self.env['account.bank.statement'].browse(statement_ids):
        #         for statement_line in statement.line_ids:
        #             if statement_line.bg_account and statement_line.bg_serial_number: # this is a bg line
        #                 self.bank_statement_auto_reconcile_bg(statement, statement_line, statement_line.bg_account, statement_line.bg_serial_number)
        #             else: # searching invoices
        #                 self.bank_statement_auto_reconcile_invoice(statement, statement_line, statement_line.name, statement_line.date, statement_line.amount)
        #         statement.period_id = self.env['account.period'].date2period(statement.date)

    @api.model
    def bank_statement_auto_reconcile_bg(self, statement, statement_line, bg_account, bg_serial_number):
        ''' Auto reconcile statement line with bg statement, create account.move. Match with bg serial number and amount '''
        statement_bg = self.env['account.bank.statement'].search([('journal_id.default_debit_account_id.name', '=', bg_account), ('bg_serial_number' , '=', bg_serial_number)])
        if len(statement_bg) == 1 and statement_line.amount == statement_bg.balance_end_real:
            entry = self.env['account.move'].create({
                'journal_id': statement.journal_id.id,
                'ref': '%s - %s' %(statement.name, statement_line.ref),
                'date': statement.date,
                'period_id': statement.period_id.id,
            })

            if entry:
                move_line_list = []
                if statement_line.amount > 0: # bg is positive, transfer amount from bg account to company main account
                    # bg account
                    move_line_list.append((0, 0, {
                        'name': statement_bg.name,
                        'account_id': statement_bg.journal_id.default_debit_account_id.id,
                        'debit': 0.0,
                        'credit': statement_line.amount,
                        'move_id': entry.id,
                    }))
                    # company main account
                    move_line_list.append((0, 0, {
                        'name': statement_bg.name,
                        'account_id': statement.journal_id.default_debit_account_id.id,
                        'debit': statement_line.amount,
                        'credit': 0.0,
                        'move_id': entry.id,
                    }))
                else: # bg is negtive, transfer amount from company main account to bg account
                    # company main account
                    move_line_list.append((0, 0, {
                        'name': statement_bg.name,
                        'account_id': statement.journal_id.default_debit_account_id.id,
                        'debit': 0.0,
                        'credit': statement_line.amount,
                        'move_id': entry.id,
                    }))
                    # bg account
                    move_line_list.append((0, 0, {
                        'name': statement_bg.name,
                        'account_id': statement_bg.journal_id.default_debit_account_id.id,
                        'debit': statement_line.amount,
                        'credit': 0.0,
                        'move_id': entry.id,
                    }))
                entry.write({
                    'line_ids': move_line_list,
                })
                entry.statement_line_id = statement_line.id
                entry.post()

    @api.model
    def bank_statement_auto_reconcile_invoice(self, statement, statement_line, partner_name, invoice_date, amount):
        ''' Create account.move. Match with account.move created by invoice '''
        partner = self.env['res.partner'].search([('name', 'ilike', partner_name)], limit=1)
        domain = [('amount_total', '=', -amount), ('period_id', '=', self.env['account.period'].date2period(statement_line.date).id)]

        # if partner:
        #    domain += [('partner_id', '=', partner.id)]
        # invoice = self.env['account.move.line'].search(domain)
        # if invoice and len(invoice) == 1:
        #     if invoice.amount_residual < invoice.amount_total: # at least one payment created for this invoice
        #         # for line in self.env['account.move.line'].search([('invoice_id', '=', invoice.id)]).filtered(lambda l: not l.statement_line_id):
        #         #     if line.credit == statement_line.amount:
        #         #         line.move_id.statement_line_id = statement_line.id
        #         # TODO: find a method to get payment move that account module does. "Open Payment" button

        #         # TODO: FIGURE OUT THE CORRECT ID COMBINATION BELOW
        #         invoice.statement_line_id = statement_line.id
        #         for line in invoice.line_ids.filtered(lambda l: l.full_reconcile_id == True):
        #             line.full_reconcile_id.reconciled_line_ids.filtered(lambda l: l.id != line.id).move_id.statement_line_id = statement_line.id


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    start_balance_calc = fields.Float(compute='_start_end_balance')
    account_number = fields.Char(string='Account Number')
    end_balance_calc = fields.Float(compute='_start_end_balance')

    def _start_end_balance(self):
        if not self.period_id:
            self.start_balance_calc = 0
            self.end_balance_calc = 0
        else:
            start_date = self.period_id.fiscalyear_id.date_start
            if len(self.line_ids.sorted(key=lambda l: l.date)) > 0:
                statement_start_date = self.line_ids.sorted(key=lambda l: l.date)[0].date
                statement_end_date = self.line_ids.sorted(key=lambda l: l.date)[-1].date
                _logger.warn('statement_start_date %s statement_end_date %s' % (statement_start_date,statement_end_date))
                self.start_balance_calc = sum(self.env['account.move.line'].search([('date', '>=', start_date), ('date', '<', statement_start_date), ('account_id', '=', self.journal_id.payment_debit_account_id.id)]).mapped('balance'))
                self.end_balance_calc = sum(self.env['account.move.line'].search([('date', '>=', statement_start_date), ('date', '<=', statement_end_date), ('account_id', '=', self.journal_id.payment_debit_account_id.id)]).mapped('balance')) + self.start_balance_calc


    bg_serial_number = fields.Char(string='BG serial number')

    #TODO: Talk about this when we reach odoo 14
    # ~ untrackable_journal_entries_count = fields.Integer(compute='_untrackable_journal_entries_count', string='Untrackable Entries')

    # ~ @api.one
    # ~ def _untrackable_journal_entries_count(self):
        # ~ self.untrackable_journal_entries_count = 1 # len(self.get_untrackable_journal_entries())

    # ~ @api.multi
    # ~ def button_untrackable_journal_entries(self):
        # ~ untrackable_move_ids = self.get_untrackable_journal_entries()
        # ~ return {
            # ~ 'name': _('Untrackable Entries'),
            # ~ 'type': 'ir.actions.act_window',
            # ~ 'res_model': 'account.move',
            # ~ 'view_type': 'form',
            # ~ 'view_mode': 'tree,form',
            # ~ 'domain': [('id', 'in', untrackable_move_ids.mapped('id'))],
            # ~ 'target': 'current',
            # ~ 'limit': 300,
            # ~ 'context': {},
        # ~ }

    # ~ @api.multi
    # ~ def get_untrackable_journal_entries(self):
        # ~ untrackable_move_ids = self.env['account.move'].browse()
        # ~ for line in self.line_ids:
            # ~ move = self.env['account.move'].search([('statement_line_id', '=', line.id)])
            # ~ attachment = self.env['ir.attachment'].search([('type', '=', 'binary'), ('res_model', '=', 'account.move'), ('res_id', '=', move.id)])
            # ~ invoice = self.env['account.invoice'].search(['|', ('move_id', '=', move.id), ('move_id', 'in', move.mapped('line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').mapped('id'))])
            # ~ voucher = self.env['account.voucher'].search(['|', ('move_id', '=', move.id), ('move_id', 'in', move.mapped('line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').mapped('id'))])
            # ~ if not attachment and not invoice and not voucher and not move.payment_order_id:
                # ~ untrackable_move_ids |= move
        # ~ _logger.warn('anders: untrackable_move_ids %s' % untrackable_move_ids.mapped('name'))
        # ~ return untrackable_move_ids

    # ~ @api.model
    # ~ def _search_untrackable_journal_entries_count(self, operator, value):
        # ~ self.env.cr.execute("select distinct move_id from account_invoice;")
        # ~ move_ids = [d['move_id'] for d in self.env.cr.dictfetchall()]
        # ~ self.env.cr.execute("select distinct move_id from account_voucher;")
        # ~ move_ids += [d['move_id'] for d in self.env.cr.dictfetchall()]
        # ~ self.env.cr.execute("select distinct res_id from ir_attachment where type='binary' and res_model='account.move';")
        # ~ move_ids += [d['res_id'] for d in self.env.cr.dictfetchall()]
        # ~ self.env.cr.execute("select id from account_move where payment_order_id is not null;")
        # ~ move_ids += [d['id'] for d in self.env.cr.dictfetchall()]
        # ~ move_ids = list(set(move_ids))
        # ~ if operator == '=':
            # ~ if value == 0:
                # ~ return [('line_ids.journal_entry_ids', 'in', move_ids)]
        # ~ if operator == '!=':
            # ~ if value == 0:
                # ~ return [('line_ids.journal_entry_ids', 'not in', move_ids)]
        # ~ raise Warning('Not implemented')

    def reconciliation_widget_preprocess(self):
        """ Get statement lines of the specified statements or all unreconciled statement lines and try to automatically reconcile them / find them a partner.
            Return ids of statement lines left to reconcile and other data for the reconciliation widget.
        """
        res = super(AccountBankStatement,self).reconciliation_widget_preprocess()
        # lines = self.env['account.bank.statement.line'].browse(res['st_lines_ids'])
        # _logger.warn('anders: XXX %s' % lines.mapped('name'))
        # ~ raise Warning(self.mapped('line_ids.journal_entry_ids.name'))
        # ~ raise Warning('Hello %s' % lines)

        statements = self
        bsl_obj = self.env['account.bank.statement.line']
        # NB : The field account_id can be used at the statement line creation/import to avoid the reconciliation process on it later on,
        # this is why we filter out statements lines where account_id is set

        sql_query = """SELECT stl.id
                        FROM account_bank_statement_line stl
                        WHERE account_id IS NULL AND not exists (select 1 from account_move m where m.statement_line_id = stl.id)
                            AND company_id = %s
                """
        params = (self.env.user.company_id.id,)
        if statements:
            sql_query += ' AND stl.statement_id IN %s'
            params += (tuple(statements.ids),)
        sql_query += ' ORDER BY stl.id'
        self.env.cr.execute(sql_query, params)
        st_lines_left = self.env['account.bank.statement.line'].browse([line.get('id') for line in self.env.cr.dictfetchall()])

        #try to assign partner to bank_statement_line
        stl_to_assign_partner = [stl.id for stl in st_lines_left if not stl.partner_id]
        refs = list(set([st.name for st in st_lines_left if not stl.partner_id]))
        if st_lines_left and stl_to_assign_partner and refs\
           and st_lines_left[0].journal_id.default_credit_account_id\
           and st_lines_left[0].journal_id.default_debit_account_id:

            sql_query = """SELECT aml.partner_id, aml.ref, stl.id
                            FROM account_move_line aml
                                JOIN account_account acc ON acc.id = aml.account_id
                                JOIN account_bank_statement_line stl ON aml.ref = stl.name
                            WHERE (aml.company_id = %s
                                AND aml.partner_id IS NOT NULL)
                                AND (
                                    (aml.statement_id IS NULL AND aml.account_id IN %s)
                                    OR
                                    (acc.internal_type IN ('payable', 'receivable') AND aml.reconciled = false)
                                    )
                                AND aml.ref IN %s
                                """
            params = (self.env.user.company_id.id, (st_lines_left[0].journal_id.default_credit_account_id.id, st_lines_left[0].journal_id.default_debit_account_id.id), tuple(refs))
            if statements:
                sql_query += 'AND stl.id IN %s'
                params += (tuple(stl_to_assign_partner),)
            self.env.cr.execute(sql_query, params)
            results = self.env.cr.dictfetchall()
            st_line = self.env['account.bank.statement.line']
            for line in results:
                st_line.browse(line.get('id')).write({'partner_id': line.get('partner_id')})

        return {
            'st_lines_ids': st_lines_left.ids,
            'notifications': [],
            'statement_name': len(statements) == 1 and statements[0].name or False,
            'num_already_reconciled_lines': 0,
        }



class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    bg_account = fields.Char(string='BG Account')
    bg_serial_number = fields.Char(string='BG Serial Number')

    def get_move_lines_for_reconciliation(self, excluded_ids=None, str=False, offset=0, limit=None, additional_domain=None, overlook_partner=False):
        """ Return account.move.line records which can be used for bank statement reconciliation.

            :param excluded_ids:
            :param str:
            :param offset:
            :param limit:
            :param additional_domain:
            :param overlook_partner:
        """
        # TODO: THIS CALL DOES NO LONGER EXIST IN ACCOUNT STATEMENT LINE. SHOULD BE REPLACED.
        res = super(AccountBankStatementLine,self).get_move_lines_for_reconciliation(excluded_ids, str, offset, limit, additional_domain, overlook_partner)
        return res.filtered(lambda line: not line.statement_id)

