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
from openerp import api,models, _, fields
from .bgmax import BgMaxParser as Parser
import re
from datetime import timedelta
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)


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
                [('acc_number', '=', self.account_no)], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0]
        return bank_account_id

    @api.multi
    def create_bg_move(self):
        if self.is_bg and not self.move_id:
            journal_id = self.get_bank_account_id().journal_id.id
            bg_account_id = self.journal_id.default_credit_account_id.id    # get money from bg account
            bank_account_id = self.get_bank_account_id().journal_id.default_debit_account_id.id   # add money to bank account
            bg_move = self.env['account.move'].create({
                'journal_id': journal_id,
                'period_id': self.period_id.id,
                'date': self.date,
                'partner_id': self.env.ref('l10n_se_bgmax.bgc').id,
                'company_id': self.company_id.id,
                'ref': self.name,
            })
            self.move_id = bg_move.id
            self.env['account.move.line'].create({
                'name': self.name,
                'account_id': bank_account_id,
                'partner_id': self.env.ref('l10n_se_bgmax.bgc').id,
                'debit': self.balance_end_real,
                'credit': 0.0,
                'move_id': bg_move.id,
            })
            self.env['account.move.line'].create({
                'name': self.name,
                'account_id': bg_account_id,
                'partner_id': self.env.ref('l10n_se_bgmax.bgc').id,
                'debit': 0.0,
                'credit': self.balance_end_real,
                'move_id': bg_move.id,
            })
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_type': 'form',
                'view_mode': 'form',
                'view_id': self.env.ref('account.view_move_form').id,
                'res_id': bg_move.id,
                'target': 'current',
                'context': {}
            }

    @api.multi
    def button_confirm_bank(self):
        res = super(account_bank_statement, self).button_confirm_bank()
        self.create_bg_move()
        return res


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
        _logger.warn("res: %s" % statements)
        #raise Warning(seb.statements)

        return statements

class account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'

    @api.model
    def get_move_lines_for_reconciliation_by_statement_line_id(self,st_line_id, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None):
        st_line = self.browse(st_line_id)
        additional_domain = additional_domain if additional_domain else [] + ['&',('date', '>=', fields.Date.to_string(fields.Date.from_string(fields.Date.today()) - timedelta(days=90))),('date', '<=', fields.Date.to_string(fields.Date.from_string(fields.Date.today()) + timedelta(days=30))),]
                                                    #~ '&',('debit', '>=', round(st_line.amount,-2) + 50.0),('debit', '<=', round(st_line.amount,-2) - 50.0)]
        _logger.error('domain %s' % additional_domain)
        if len(str) > 0:
            additional_domain += ['|',('invoice.number', '=', str),'|',('invoice.origin', 'ilike', str),('invoice.name', 'ilike', str)]
            #~ additional_domain += ['|',('invoice.number', '=', str)]
        #~ st_line = self.browse(cr, uid, st_line_id, context=context)
        return super(account_bank_statement_line,self).get_move_lines_for_reconciliation_by_statement_line_id(st_line_id, excluded_ids, str, offset, limit, count, additional_domain)

    def XXX_domain_move_lines_for_reconciliation(self, cr, uid, st_line, excluded_ids=None, str=False, additional_domain=None, context=None):
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []
        # Make domain
        domain = additional_domain + [
            ('reconcile_id', '=', False),
            ('state', '=', 'valid'),
            ('account_id.reconcile', '=', True)
        ]
        if st_line.partner_id.id:
            domain += [('partner_id', '=', st_line.partner_id.id)]
        if excluded_ids:
            domain.append(('id', 'not in', excluded_ids))
        if str:
            domain += [
                '|', ('move_id.name', 'ilike', str),
                '|', ('move_id.ref', 'ilike', str),
                ('date_maturity', 'like', str),
            ]
            if not st_line.partner_id.id:
                domain.insert(-1, '|', )
                domain.append(('partner_id.name', 'ilike', str))
            if str != '/':
                domain.insert(-1, '|', )
                domain.append(('name', 'ilike', str))
        return domain

    #~ def _domain_reconciliation_proposition(self, cr, uid, st_line, excluded_ids=None, context=None):
        #~ if excluded_ids is None:
            #~ excluded_ids = []
        #~ domain = [('ref', '=', st_line.name.strip()),
                  #~ ('reconcile_id', '=', False),
                  #~ ('state', '=', 'valid'),
                  #~ ('account_id.reconcile', '=', True),
                  #~ ('id', 'not in', excluded_ids),
                  #~ ('date', '>=', fields.Date.to_string(fields.Date.from_string(fields.Date.today()) - timedelta(days=90))),]
        #~ if st_line.partner_id:
            #~ domain.append(('partner_id', '=', st_line.partner_id.id))
        #~ _logger.warn('>>>>>> domain: %s' %domain)
        #~ return domain
