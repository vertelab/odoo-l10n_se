# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
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
from openerp import api,models, _
from .bgmax import BgMaxParser as Parser
import re
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'


    @api.model
    def _parse_file(self, data_file):
        """Parse a BgMax  file."""
        parser = Parser()
        #~ statements = parser.parse(data_file)
        try:
            _logger.debug("Try parsing with bgmax.")
            statements = parser.parse(data_file)
            #_logger.debug("statemenst: %s" % statements)
        except ValueError, e:
            _logger.error("Error in BgMax file. (%s)", e)
            raise Warning("Error in BgMax file. (%s)" % e)
        except Exception,e:
            # Not a BgMax file, returning super will call next candidate:
            _logger.info("Statement file was not a BgMax file. (%s)", e)
            return super(AccountBankStatementImport, self)._parse_file(data_file)

        fakt = re.compile('\d+')  # Pattern to find invoice numbers
        for s in statements:
            for t in s['transactions']:
                partner = None
                #~ _logger.error('---> account_number %s ' % (t.get('account_number','no account')))
                if t.get('account_number',None):
                    partner = self.env['res.partner.bank'].search([('acc_number','ilike',t['account_number'])],limit=1).mapped('partner_id')                    
                if not partner:
                    vat = 'SE%s01' % t['partner_name'][2:]
                    name1 = t['partner_name'].strip()
                    name2 = name1.upper().replace(' AB','').replace('AKTIEBOLAG','').replace(' HB','').replace('HANDELSBOLAG','').replace(' KB','').replace('KOMMANDITBOLAG','').replace('FIRMA','').strip()
                    partner = self.env['res.partner'].search(['|','|',('name','ilike',name1),('name','ilike',name2),('vat','=',vat)],limit=1)
                    #~ _logger.error('----> NAME name1=%s| name2=%s| vat %s partner %s' % (name1,name2,vat,partner))
                if partner:
                    if t['account_number'] and not partner.bank_ids:
                        partner.bank_ids = [(0,False,{'acc_number': t['account_number'],'state': 'bg'})]
                    t['account_number'] = partner.bank_ids and partner.bank_ids[0].acc_number or ''
                    t['partner_id'] = partner.id
                else:    
                    fnr = '-'.join(fakt.findall(t['name']))
                    if fnr:
                        invoice = self.env['account.invoice'].search(['|',('name','ilike',fnr),('supplier_invoice_number','ilike',fnr)])
                        if invoice:
                            t['account_number'] = invoice[0] and  invoice[0].partner_id.bank_ids and invoice[0].partner_id.bank_ids[0].acc_number or ''
                            t['partner_id'] = invoice[0] and invoice[0].partner_id.id or None
                        #~ _logger.error('---> fnr %s  invoice %s' % (fnr,invoice if invoice else 'no invoice'))
                _logger.error('----> partner %s vat %s account_number %s' % (t.get('partner_id','no partner'+t['partner_name']),vat,t.get('account_number','no account')))
        #~ res = parser.parse(data_file)
        _logger.debug("res: %s" % statements)
        #raise Warning(seb.statements)

        return statements
