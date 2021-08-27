# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
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
from odoo import api, models, _, fields
from .bgmax import BgMaxParser as Parser
from .bgmax import BgMaxGenerator as BgMaxGen
from .bgmax import BgExcelTransactionReport as BgExcelParser
import re
import base64
from datetime import timedelta
from odoo.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        """ Returns a list of strings representing the supported import formats.
        """
        return super(AccountJournal, self)._get_bank_statements_available_import_formats() + ['bgmax']

class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    connected_journal_id = fields.Many2one(comodel_name='account.journal', string='Connected Journal')


class account_bank_statement(models.Model):
    _inherit = 'account.bank.statement'

    is_bg = fields.Boolean(string='Is Bankgiro')
    account_no = fields.Char(string='Account Number')
    move_id = fields.Many2one(comodel_name='account.move', string='Account Move')

    @api.model
    def get_bank_account_id(self):
        bank_account_id = None
        if self.account_no and len(self.account_no) > 4:
            bank_account_ids = self.env['res.partner.bank'].search(
                [('acc_number', '=', self.account_no[:4] + self.account_no[4:].lstrip('0'))], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0]
        return bank_account_id

    @api.multi
    def create_bg_move(self):
        for statement in self:
            if statement.is_bg and not statement.move_id:
                # ~ journal_id = statement.get_bank_account_id().journal_id.id
                journal_id = statement.journal_id.id
                bg_account_id = statement.journal_id.default_credit_account_id.id    # get money from bg account
                # ~ bank_account_id = statement.journal_id.default_debit_account_id.id   # add money to bank account
                bank_account_id = statement.get_bank_account_id().connected_journal_id.default_debit_account_id.id   # add money to bank account
                bg_move = self.env['account.move'].create({
                    'journal_id': journal_id,
                    'period_id': statement.period_id.id,
                    'date': statement.date,
                    'partner_id': statement.env.ref('l10n_se_bgmax.bgc').id,
                    'company_id': statement.company_id.id,
                    'ref': statement.name,
                })
                statement.move_id = bg_move.id
                move_line_list = []
                move_line_list.append((0, 0, {
                    'name': statement.name,
                    'account_id': bank_account_id,
                    'partner_id': statement.env.ref('l10n_se_bgmax.bgc').id,
                    'debit': statement.balance_end_real,
                    'credit': 0.0,
                    'move_id': bg_move.id,
                }))
                move_line_list.append((0, 0, {
                    'name': statement.name,
                    'account_id': bg_account_id,
                    'partner_id': statement.env.ref('l10n_se_bgmax.bgc').id,
                    'debit': 0.0,
                    'credit': statement.balance_end_real,
                    'move_id': bg_move.id,
                }))
                bg_move.write({
                    'line_ids': move_line_list,
                })
        #~ return {
            #~ 'type': 'ir.actions.act_window',
            #~ 'res_model': 'account.move',
            #~ 'view_type': 'form',
            #~ 'view_mode': 'form',
            #~ 'view_id': self.env.ref('account.view_move_form').id,
            #~ 'res_id': bg_move.id,
            #~ 'target': 'current',
            #~ 'context': {}
        #~ }

    @api.multi
    def button_confirm_bank(self):
        res = super(account_bank_statement, self).button_confirm_bank()
        self.create_bg_move()
        return res

    @api.multi
    def get_untrackable_journal_entries(self):
        untrackable_move_ids = super(account_bank_statement,self).get_untrackable_journal_entries() or self.env['account.move'].browse()
        for line in self.line_ids:
            move = self.env['account.move'].search([('statement_line_id', '=', line.id)])
            reconciled_bg = False
            for ml in move.line_ids:
                bg_statement = self.env['account.bank.statement'].search([('is_bg', '=', True), ('name', '=', ml.name), '|', ('line_ids.amount', '=', ml.balance), ('line_ids.amount', '=', -ml.balance)])
                reconciled_bg = True if len(bg_statement) > 0 else False
            if not reconciled_bg:
                untrackable_move_ids |= move
        _logger.warn('anders: untrackable_move_ids %s (bg)' % untrackable_move_ids.mapped('name'))
        return untrackable_move_ids


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse a BgMax  file."""
        parser = Parser()
        try:
            _logger.info(u"Try parsing with bgmax.")
            statements = parser.parse(data_file)
        except ValueError as e:
            _logger.info(u"Statement file was not a BgMax file.")
            try:
                excelParser = BgExcelParser(data_file)
                _logger.info(u"Try parsing BgMax excel document.")
                statements = excelParser.parse()
            except ValueError:
                    _logger.info(u"Statement was not a BgMax excel document.")
                    return super(AccountBankStatementImport, self)._parse_file(data_file)

        fakt = re.compile('\d+') # Pattern to find invoice numbers
        for s in statements:
            for t in s['transactions']:
                partner = None
                if t.get('account_number',None):
                    partner = self.env['res.partner.bank'].search([('acc_number','ilike',t['account_number'])],limit=1).mapped('partner_id')
                if not partner:
                    if t['partner_name']:
                        vat = 'SE%s01' % t['partner_name'][2:]
                        name1 = t['partner_name'].strip()
                        name2 = name1.upper().replace(' AB','').replace('AKTIEBOLAG','').replace(' HB','').replace('HANDELSBOLAG','').replace(' KB','').replace('KOMMANDITBOLAG','').replace('FIRMA','').strip()
                        partner = self.env['res.partner'].search(['|','|',('name','ilike',name1),('name','ilike',name2),('vat','=',vat)],limit=1)
                        _logger.error('----> partner %s vat %s account_number %s' % (t.get('partner_id','no partner'+t['partner_name']),vat,t.get('account_number','no account')))
                   
                if partner:
                    if t['account_number'] and not partner.bank_ids:
                        partner.bank_ids = [(0,False,{'acc_number': t['account_number'],'state': 'bg'})]
                    t['account_number'] = partner.bank_ids and partner.bank_ids[0].acc_number or ''
                    t['partner_id'] = partner.id
                else:
                    fnr = '-'.join(fakt.findall(t['name']))
                    if fnr:
                        invoice = self.env['account.invoice'].search([('name','ilike',fnr)])
                        if invoice:
                            t['account_number'] = invoice[0] and  invoice[0].partner_id.bank_ids and invoice[0].partner_id.bank_ids[0].acc_number or ''
                            t['partner_id'] = invoice[0] and invoice[0].partner_id.id or None
        currency_code = statements[0].get('currency_code')
        account_number = statements[0].get('account_number')
        account_number = account_number[:4] + account_number[4:].lstrip('0')
        _logger.warn(statements)
        return currency_code, account_number, statements


class account_payment_order(models.Model):
    _inherit = 'account.payment.order'

    @api.model
    def _set_bank_payment_line_seq(self):
        self.env.ref('account_payment_order.bank_payment_line_seq').sudo().write({'prefix': ''})

    @api.one
    def create_bgmax(self):
        bggen = BgMaxGen()
        bg_account = self.env['res.partner.bank'].search([('partner_id', '=', self.env.user.company_id.partner_id.id), ('acc_type', '=', 'bankgiro')])
        if len(bg_account) > 0:
            bg_account = bg_account[0].acc_number.replace('-', '').replace(' ', '')
        else:
            bg_account = '0000000000'
        data = bggen.generate(self, bg_account, self.env.user.company_id)
        self.env['ir.attachment'].create({
            'type': 'binary',
            'name': 'BANKGIROINBETALNINGAR%s1.txt' % fields.Date.today(),
            'datas': base64.b64encode(data.encode('iso8859-1', 'replace')),
            'res_model': self._name,
            'res_id': self.id,
        })
