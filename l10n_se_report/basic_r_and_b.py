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


    def get_balance(self,code):
        return self.env['account.account'].seach([('code','=',code)])[0].balance

    @api.multi
    def print_basic_r_and_b(self):
        for w in self:
            data = {}
            data['ids'] = [w.id]            
            data['model'] = 'l10n_se_report.basic_r_and_b.wizard'
            
            data = self.read(cr, uid, ids, context=context)[0]
            datas = {
            'ids': student_ids,
            'model': 'wiz.student.report', # wizard model name
            'form': data,
            'context':context
            }
            return {
                   'type': 'ir.actions.report.xml',
                   'report_name': 'school_management.report_student_master_qweb',#module name.report template name
                   'datas': datas,
               }
            
             
            
            response = http.request.render('l10n_se_report.basic_r_and_b', {
                'context_value': 42
            })
            raise Warning(_("%s" % response)) 
            return w.env['report'].with_context({
                'initial_bal': w.initial_bal,
                'chart_account_id': w.chart_account_id.id,
                'fiscalyear_id': w.fiscalyear_id.id,
                'target_move': w.target_move
            }).get_action(self,'l10n_se_report.basic_r_and_b',data=data)

        
        
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
