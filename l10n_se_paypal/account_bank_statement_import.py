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
from odoo import api,models,fields, _
from .paypal import PaypalTransaktionsrapportType as Parser
import base64
import re
from datetime import timedelta
import logging
_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add PayPal method to account.bank.statement.import."""
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
            _logger.info(u"Try parsing with PayPal Report file.")
            parser = Parser(base64.b64decode(self.data_file))
        except ValueError:
            _logger.info(u"Statement file was not a PayPal Report file.")
            return super(AccountBankStatementImport, self)._parse_file(data_file)

        paypal = parser.parse()
        for s in paypal.statements:
            move_line_ids = []
            currency = self.env['res.currency'].search([('name','=', s['currency_code'])])
            for t in s['transactions']:
                t['currency_id'] = currency.id
                # ~ partner_id = self.env['res.partner'].search(['|',('name','ilike',t['partner_name']),('ref','ilike',t['partner_name'])])
                # ~ if partner_id:
                    # ~ t['account_number'] = partner_id[0].commercial_partner_id.bank_ids and partner_id[0].commercial_partner_id.bank_ids[0].acc_number or ''
                    # ~ t['partner_id'] = partner_id[0].commercial_partner_id.id
                d1 = fields.Date.to_string(fields.Date.from_string(t['date']) - timedelta(days=5))
                d2 = fields.Date.to_string(fields.Date.from_string(t['date']) + timedelta(days=40))
                line = self.env['account.move.line'].search([('move_id.date', '=', t['date']), ('balance', '=', t['amount']), ('name', '=', str(t['ref']))])
                if len(line) > 0:
                    if line[0].move_id.state == 'draft' and line[0].move_id.date != t['date']:
                        line[0].move_id.date = t['date']
                    t['journal_entry_id'] = line[0].move_id.id
                    for line in line[0].move_id.line_ids:
                        move_line_ids.append(line)
            s['move_line_ids'] = [(6, 0, [l.id for l in move_line_ids])]

        _logger.debug("res: %s" % paypal.statements)
        return paypal.account_currency, paypal.account_number, paypal.statements


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
