# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import http
from openerp.http import request
from openerp import SUPERUSER_ID

from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import time

from openerp.tools.safe_eval import safe_eval as eval

import logging
_logger = logging.getLogger(__name__)



# ---------------------------------------------------------
# Account Entries Models
# ---------------------------------------------------------

class account_model(models.Model):
    _inherit = "account.model"

    python_code = fields.Text('Python Code',default="""# Available variables:
#----------------------
# model: object containing the model
# move: account.move object
# user: object current user
# context: current context
#""")
    python_legend = fields.Text(readonly=True, size=100,default=_("""
Python Code:
# Available variables (model):
#----------------------
# model: object containing the model
# move: account.move object
# user: object current user
# context: current context
# 
# example: move.write({'field': data})
#
# Available variables (line):
#----------------------
# model: object containing the model
# move:  object containing the move
# user: object current user
# move_line: dict for creating account.move.line (to be returned)
# 'name','quantity','debit','credit','account_id','account_tax_id','move_id','partner_id','date','date_maturity'
# context: current context
#
# example:  move_line['field'] = data

"""))

    @api.v7
    def _eval(self,cr,uid,ids,model,move_id,context=None):   # runs python code
        try: 
            eval(model.python_code,{
                'model': model,
                'move': self.pool.get('account.move').browse(cr,uid,move_id),
                'user': self.pool.get('res.users').browse(cr,uid,uid),
                'context': context,
            }, mode='exec', nocopy=True)
        except:
            raise Warning(_('Wrong python code defined for model %s (%s).')% (model.name, model.python_code)) 

    @api.v7
    def generate(self, cr, uid, ids, data=None, context=None):
        _logger.warning('generate start %s' % ids)
        if data is None:
            data = {}
        move_ids = []
        entry = {}
        account_move_obj = self.pool.get('account.move')
        account_move_line_obj = self.pool.get('account.move.line')
        pt_obj = self.pool.get('account.payment.term')
        period_obj = self.pool.get('account.period')

        if context is None:
            context = {}

        if data.get('date', False):
            context = dict(context)
            context.update({'date': data['date']})

        move_date = context.get('date', time.strftime('%Y-%m-%d'))
        move_date = datetime.strptime(move_date,"%Y-%m-%d")
        for model in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
            ctx.update({'company_id': model.company_id.id})
            period_ids = period_obj.find(cr, uid, dt=context.get('date', False), context=ctx)
            period_id = period_ids and period_ids[0] or False
            ctx.update({'journal_id': model.journal_id.id,'period_id': period_id})
            try:
                entry['name'] = model.name%{'year': move_date.strftime('%Y'), 'month': move_date.strftime('%m'), 'date': move_date.strftime('%Y-%m')}
            except:
                raise osv.except_osv(_('Wrong Model!'), _('You have a wrong expression "%(...)s" in your model!'))
            move_id = account_move_obj.create(cr, uid, {
                'ref': entry['name'],
                'period_id': period_id,
                'journal_id': model.journal_id.id,
                'date': context.get('date', time.strftime('%Y-%m-%d'))  # changed
            })
            move_ids.append(move_id)
            self._eval(cr,uid,ids,model,move_id,context=context)
            for line in model.lines_id:
                analytic_account_id = False
                if line.analytic_account_id:
                    if not model.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal!'),_("You have to define an analytic journal on the '%s' journal!") % (model.journal_id.name,))
                    analytic_account_id = line.analytic_account_id.id
                val = {
                    'move_id': move_id,
                    'journal_id': model.journal_id.id,
                    'period_id': period_id,
                    'analytic_account_id': analytic_account_id
                }

                date_maturity = context.get('date',time.strftime('%Y-%m-%d'))
                if line.date_maturity == 'partner':
                    if not line.partner_id:
                        raise osv.except_osv(_('Error!'), _("Maturity date of entry line generated by model line '%s' of model '%s' is based on partner payment term!" \
                                                                "\nPlease define partner on it!")%(line.name, model.name))

                    payment_term_id = False
                    if model.journal_id.type in ('purchase', 'purchase_refund') and line.partner_id.property_supplier_payment_term:
                        payment_term_id = line.partner_id.property_supplier_payment_term.id
                    elif line.partner_id.property_payment_term:
                        payment_term_id = line.partner_id.property_payment_term.id
                    if payment_term_id:
                        pterm_list = pt_obj.compute(cr, uid, payment_term_id, value=1, date_ref=date_maturity)
                        if pterm_list:
                            pterm_list = [l[0] for l in pterm_list]
                            pterm_list.sort()
                            date_maturity = pterm_list[-1]

                val.update({
                    'name': line.name,
                    'quantity': line.quantity,
                    'debit': line.debit,
                    'credit': line.credit,
                    'account_id': line.account_id.id,
                    'account_tax_id': line.line_tax_id.id,  # This is the addition, it has to be done here or never #1185 account_move_line.py ('You cannot change the tax, you should remove and recreate lines')
                    'move_id': move_id,
                    'partner_id': line.partner_id.id,
                    'date': context.get('date', time.strftime('%Y-%m-%d')),  # changed
                    'date_maturity': date_maturity
                })
                val = self.pool.get('account.model.line')._eval(cr,uid,line.id,model,move_id,val,context=ctx)
                self.pool.get('account.move.line').create(cr, uid, val, context=ctx)
        _logger.warning('generate stop %s' % move_ids)
        
        return move_ids


class account_model_line(models.Model):
    _inherit = 'account.model.line'

    
    line_tax_id = fields.Many2many('account.tax',
        'account_model_line_tax', 'model_line_id', 'tax_id',
        string='Taxes', )
    python_code = fields.Text('Python Code',default='')

    @api.v7
    def _eval(self, cr, uid,id, model,move_id,move_line,context=None):   # runs python code
        line = self.pool.get('account.model.line').browse(cr,uid,id)
        if not line.python_code:
            return move_line
        try:
            eval(line.python_code, {
                'model': model,
                'move': self.pool.get('account.move').browse(cr,uid,move_id),
                'move_line': move_line,
                'context': context,
                'user': self.pool.get('res.users').browse(cr,uid,uid),
                'line': line,
                }, mode='exec', nocopy=True)
            return move_line
        except:
            raise Warning(_('Wrong python code defined for model %s line %s %s (%s).')% (model.name, line.sequence, line.name, line.python_code)) 

    #
    # Set the tax field according to the account and the fiscal position
    #
    @api.onchange('account_id')
    def onchange_account_id(self):
        self.line_tax_id = self.account_id.tax_ids # fiscal position ?
   
