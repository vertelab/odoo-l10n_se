# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013-2016 Vertel AB <http://vertel.se>
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
import logging
from odoo import api,models,fields, _
from .seb import SEBTransaktionsrapport as Parser
from .seb import SEBTransaktionsrapportType1 as Parser1
from .seb import SEBTransaktionsrapportType2 as Parser2
from .seb import SEBTransaktionsrapportType3 as Parser3
import base64
import re

from openerp.osv import osv

from io import StringIO
from zipfile import ZipFile, BadZipfile  # BadZipFile in Python >= 3.2
from datetime import timedelta


_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        """ Returns a list of strings representing the supported import formats.
        """
        return super(AccountJournal, self)._get_bank_statements_available_import_formats() + ['seb']

class AccountBankStatementImport(models.TransientModel):
    """Add seb method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse one file or multiple files from zip-file.
        Return array of statements for further processing.
        xlsx-files are a Zip-file, have to override
        """
        statements = []
        files = [data_file]

        try:
            _logger.info(u"Try parsing with SEB Kontohändelser document.")
            parser = Parser(base64.b64decode(self.data_file))
        except ValueError:
            # Not a SEB Kontohändelser document, returning super will call next candidate:
            _logger.info(u"Statement file was not a SEB Kontohändelser document.")
            try:
                _logger.info(u"Try parsing with SEB Typ 1 Kontohändelser.")
                parser = Parser1(base64.b64decode(self.data_file))
            except ValueError:
                # Not a SEB Type 2 file, returning super will call next candidate:
                _logger.info(u"Statement file was not a SEB Type 1 Kontohändelse file.")
                try:
                    _logger.info(u"Try parsing with SEB Typ 2 Kontohändelser.")
                    parser = Parser2(base64.b64decode(self.data_file))
                except ValueError:
                    # Not a SEB Type 3 file, returning super will call next candidate:
                    _logger.info(u"Statement file was not a SEB Type 2 Kontohändelse file.")
                    try:
                        _logger.info(u"Try parsing with SEB Typ 3 Kontohändelser.")
                        parser = Parser3(base64.b64decode(self.data_file))
                    except ValueError:
                        # Not a SEB Type 3 file, returning super will call next candidate:
                        _logger.info(u"Statement file was not a SEB Type 3 Kontohändelse file.")
                        return super(AccountBankStatementImport, self)._parse_file(data_file)

        seb = parser.parse()
        for s in seb.statements:
            currency = self.env['res.currency'].search([('name','=',s['currency_code'])])
            account = self.env['res.partner.bank'].search([('acc_number','=',s['account_number'])]).mapped('journal_id').mapped('default_debit_account_id')
            move_line_ids = []
            for t in s['transactions']:
                if s['currency_code'] != currency.name:
                    t['currency_id'] = currency.id
                partner_id = self.env['res.partner'].search(['|',('name','ilike',t['partner_name']),('ref','ilike',t['partner_name'])])
                if partner_id:
                    t['account_number'] = partner_id[0].commercial_partner_id.bank_ids and partner_id[0].commercial_partner_id.bank_ids[0].acc_number or ''
                    t['partner_id'] = partner_id[0].commercial_partner_id.id
                # ~ d1 = fields.Date.to_string(fields.Date.from_string(t['date']) - timedelta(days=5))
                # ~ d2 = fields.Date.to_string(fields.Date.from_string(t['date']) + timedelta(days=40))

                # ~ invoice = None
                # ~ voucher = None
                # ~ invoice = self.env['account.invoice'].search([('date_invoice','>',d1),('date_invoice','<',d2)])
                # ~ if invoice:
                    # ~ t['account_number'] = invoice[0] and invoice[0].partner_id.bank_ids and invoice[0].partner_id.bank_ids[0].acc_number or ''
                    # ~ t['partner_id'] = invoice[0] and invoice[0].partner_id.id or None
                # ~ vouchers = self.env['account.voucher'].search([('date','>',d1),('date','<',d2), ('account_id', '=', account.id)])
                # ~ if len(vouchers) > 0:
                    # ~ voucher_partner = vouchers.filtered(lambda v: v.partner_id == partner_id and round(v.amount, -1) == round(t['amount'], -1))
                    # ~ if len(voucher_partner) > 0:
                        # ~ voucher = voucher_partner[0]
                    # ~ else:
                        # ~ voucher = vouchers.filtered(lambda v: round(v.amount, -1) == round(t['amount'], -1))[0] if vouchers.filtered(lambda v: round(v.amount, -1) == round(t['amount'], -1)) else None
                # ~ if not invoice or not voucher:  # match with account.move
                    # ~ line = self.env['account.move'].search([('date','>',d1),('date','<',d2)]).filtered(lambda l: l.account_id == account and round(l.debit-l.credit, -1) == round(t['amount'], -1))
                    # ~ if len(line)>0:
                        # ~ if line[0].move_id.state == 'draft' and line[0].move_id.date != t['date']:
                            # ~ line[0].move_id.date = t['date']
                        # ~ move = line.mapped('move_id')[0] if len(line)>0 else None
                        # ~ if move:
                            # ~ t['journal_entry_ids'] = move.id
                            # ~ for line in move.line_ids:
                                # ~ move_line_ids.append(line)
                            # ~ t['voucher_id'] = self.env['account.voucher'].search([('move_id', '=', move.id)]).id if self.env['account.voucher'].search([('move_id', '=', move.id)]) else None
                # ~ elif voucher:   # match with account.voucher
                    # ~ if voucher.move_id.state == 'draft' and voucher.move_id.date != t['date']:
                        # ~ voucher.move_id.date = t['date']
                    # ~ if voucher.state == 'draft' and voucher.date != t['date']:
                        # ~ voucher.date = t['date']
                    # ~ t['journal_entry_ids'] = voucher.move_id.id
                    # ~ for line in voucher.move_id.line_ids:
                        # ~ move_line_ids.append(line)
                    # ~ t['voucher_id'] = voucher.id
                # ~ elif invoice:   # match with account.invoice
                    # ~ line = invoice.payment_ids.filtered(lambda l: l.date > d1 and l.date < d2 and round(l.debit-l.credit, -1) == round(t['amount'], -1))
                    # ~ if len(line) > 0:
                        # ~ if line[0].move_id.state == 'draft' and line[0].move_id.date != t['date']:
                            # ~ line[0].move_id.date = t['date']
                        # ~ t['journal_entry_ids'] = line[0].move_id.id
                        # ~ for line in line[0].move_id.line_ids:
                            # ~ move_line_ids.append(line)
            s['move_line_ids'] = [(6, 0, [l.id for l in move_line_ids])]

        #~ res = parser.parse(data_file)
        _logger.debug("res: %s" % seb.statements)
        #~ raise Warning(seb.statements)
        return seb.account_currency, seb.account_number, seb.statements


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    bg_serial_number = fields.Char(string='BG serial number')




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
