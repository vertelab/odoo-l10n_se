# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2015-2016 Vertel AB <http://vertel.se>
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
from openerp import api,models,fields, _
from .stripe import StripePaymentsReport as Parser
import cStringIO
import uuid
import base64

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add Stripe method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    filename = fields.Char("File Name")
    
    @api.model
    def _parse_file(self, data_file):
        """Parse one file or multiple files from zip-file.
        Return array of statements for further processing.
        xlsx-files are a Zip-file, have to override
        """

        try:
            statement_import_id = self.env['account.bank.statement.import'].browse(self.env.context.get('active_id', False))
            parser = Parser(data_file, filename=statement_import_id.filename)
        except ValueError:
            _logger.info(u"Statement file was not a Stripe Report file.")
            return super(AccountBankStatementImport, self)._parse_file(data_file)
            

        stripe = parser.parse()
        for s in stripe.statements:
            currency = self.env['res.currency'].search([('name','=',s['currency_code'])])
            move_line_ids = []
            for t in s['transactions']:
                sale_order_name = t['ref'][:-2]
                sale_order = self.env['sale.order'].search([('name','=',sale_order_name)], limit=1)
                # ~ if len(sale_order) > 0 and sale_order.invoice_ids[0].state == 'paid':
                    # ~ s.end_balance -= t['amount']
                    # ~ s['transactions'].remove(t)
                    # ~ _logger.info('Removed transaction, was already paid: {}'.format(sale_order_name))
                    # ~ continue
            
                t['currency_id'] = currency.id
                partner_id = self.env['res.partner'].search([('email', 'ilike', t['name'].split(',')[0])], limit=1)
                if partner_id:
                    t['account_number'] = partner_id.commercial_partner_id.bank_ids and partner_id.commercial_partner_id.bank_ids[0].acc_number or ''
                    t['partner_id'] = partner_id.commercial_partner_id.id

                reference = '{} ({})'.format(partner_id.name, sale_order_name)
                account_move = self.env['account.move'].search([('ref', '=', reference)])
                line = account_move.line_id
                if sale_order_name and len(line) > 0:
                    sale_order = self.env['sale.order'].search([('name','=',sale_order_name)], limit=1)
                    if line[0].move_id.state == 'draft':
                        line[0].move_id.date = t['date']
                        t['journal_entry_id'] = line[0].move_id.id
                    for line in line[0].move_id.line_id:
                        move_line_ids.append(line)
            _logger.info('appending move line ids: {}'.format(move_line_ids))
            s['move_line_ids'] = [(6, 0, [l.id for l in move_line_ids])]

        return stripe.account_currency, stripe.account_number, stripe.statements

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
