# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016- Vertel AB (<http://www.vertel.se>).
#
#    This progrupdateam is free software: you can redistribute it and/or modify
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
from openerp.exceptions import Warning
from openerp import http
from openerp.http import request

from datetime import timedelta, date
import datetime
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT


import logging
_logger = logging.getLogger(__name__)

class basic_r_and_b_wizard(models.TransientModel):
    _name = "l10n_se_report.basic_r_and_b.wizard"

 

    chart_account_id = fields.Many2one('account.account', string='Chart of Account', help='Select Charts of Accounts', required=True, domain = [('parent_id','=',False)])
    fiscalyear_id = fields.Many2one('account.fiscalyear', string='Fiscal Year', required=True)
    target_move =   fields.Selection([('posted', 'All Posted Entries'),
                                     ('all', 'All Entries'),
                                ], string='Target Moves', required=True)
    initial_bal = fields.Boolean(string="With initial balance")


    def get_account(self,code,prev=False):
        #raise Warning("code '%s'" % code)
        if prev:
            if self.get_prev_fiscalyear():                
                accounts = self.env['account.account'].with_context({'fiscalyear_id': self.get_prev_fiscalyear().id}).search([('code','=',code)])
            else:
                accounts = False
        else:
            accounts = self.env['account.account'].search([('code','=',code)])
        if accounts and len(accounts) > 1:
            return accounts[0]
        elif accounts:
            return accounts
        return False

            
    def get_label(self,code):
        return self.get_account(code) and '%s %s' % (code,self.get_account(code).name) or 'Code %s' % code 
        #~ accounts = self.env['account.account'].search([('code','=',code)])
        #~ if accounts and len(accounts) > 1:
            #~ _logger.warning('Label %s' % accounts[0].name)
            #~ return '%s %s' % (code,accounts[0].name)
        #~ elif accounts:
            #~ _logger.warning('Label %s' % accounts.name)
            #~ return 
        #~ _logger.warning('Label %s' % code)

    def get_balance(self,code,prev=False):
        balance = self.get_account(code,prev) and self.get_account(code,prev).balance
        if balance and balance < 0:
            balance *= -1
        return balance and '%7.0f' % balance or False


    def get_fiscalyear(self,year_id=None,date=None,prev=False):
        if prev:
            return self.get_fiscalyear(date=datetime.datetime.strptime(self.get_fiscalyear().date_start,DEFAULT_SERVER_DATE_FORMAT) - timedelta(days=30))
        if year_id:
            return self.env['account.fiscalyear'].browse(year_id)
        if date:
            year = False
            try:
                year = self.env['account.fiscalyear'].browse(self.env['account.fiscalyear'].finds(date)[0])
            except:
                pass
            return year
        return self.env['account.fiscalyear'].browse(self._context.get('fiscalyear_id',1))
 
    @api.multi
    def print_basic_r_and_b(self):
        for w in self:
            data = {}
            data['ids'] = [w.id]            
            data['model'] = 'l10n_se_report.basic_r_and_b.wizard'
            
            #~ data = self.read(cr, uid, ids, context=context)[0]
            #~ datas = {
            #~ 'ids': student_ids,
            #~ 'model': 'wiz.student.report', # wizard model name
            #~ 'form': data,
            #~ 'context':context
            #~ }
            #~ return {
                   #~ 'type': 'ir.actions.report.xml',
                   #~ 'report_name': 'school_management.report_student_master_qweb',#module name.report template name
                   #~ 'datas': datas,
               #~ }
            
             
            
            #~ response = http.request.render('l10n_se_report.basic_r_and_b', {
                #~ 'context_value': 42
            #~ })
            #~ raise Warning(_("%s" % response)) 
            return w.env['report'].with_context({
                'initial_bal': w.initial_bal,
                'chart_account_id': w.chart_account_id.id,
                'fiscalyear_id': w.fiscalyear_id.id,
                'target_move': w.target_move
            }).get_action(self,'l10n_se_report.basic_r_and_b',data=data)

        
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
