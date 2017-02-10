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
import werkzeug
import pytz
import re
import base64
from fnmatch import fnmatch,fnmatchcase
from lxml import etree
import openerp.tools as tools
import openerp.tools.misc as misc
from tempfile import TemporaryFile

try:
    import openpyxl
except ImportError:
    raise Warning('excel library missing, pip install openpyxl')

try:
    from xlrd import open_workbook
except ImportError:
    raise Warning('excel library missing, pip install xlrd')



import logging
_logger = logging.getLogger(__name__)

class import_chart_of_account(models.TransientModel):
    _name = 'import.chart.template'

    data = fields.Binary('File')
    @api.one
    def _data(self):
        self.xml_file = self.data
    xml_file = fields.Binary(compute='_data')
    state =  fields.Selection([('choose', 'choose'), ('get', 'get')],default="choose")
    result = fields.Text(string="Result",default='')


   
    @api.multi
    def send_form(self,):
        chart = self[0]
        #_logger.warning('data %s b64 %s ' % (account.data,base64.decodestring(account.data)))
        #~ raise Warning('data %s b64 %s ' % (chart.data.encode('utf-8'),base64.decodestring(chart.data.encode('utf-8'))))
        
        if not chart.data == None:
            
            wb = open_workbook(file_contents=base64.decodestring(chart.data))
            #~ wb = open_workbook(file_contents=chart.data)
            ws = wb.sheet_by_index(0)
            basic_code = u' \u25a0'
            not_k2 = u'[Ej K2]'
                
            nbr_lines = ws.nrows
            user_type = 'account.data_account_type_asset'

            #~ self.env['account.account.template'].search([('chart_template_id', '=',self.id),('code','>','1000'),('code','<','9999')]).unlink()
            #~ self.env['account.account.template'].search([('chart_template_id', '=',self.id),('code','>','10'),('code','<','99')]).unlink()
            #~ self.env['account.account.template'].search([('chart_template_id', '=',self.id),('code','>','1'),('code','<','9')]).unlink()
            #~ self.env['account.account.template'].search([('chart_template_id', '=',self.id)]).unlink()
            _logger.warn('Accounts %s' % self.env['account.account.template'].search([('code','like','%.0')]))
            self.env['account.account.template'].search([('code','like','%.0')]).unlink()
            #~ self.env['account.account.template'].search([('code','>','10'),('code','<','99')]).unlink()
            #~ self.env['account.account.template'].search([('code','>','1'),('code','<','9')]).unlink()
            #~ self.env['account.account.template'].search([]).unlink()
            
            template = self.env['account.chart.template'].search([])[-1]
            
            chart_template_titles = template.copy({'name': 'Title'})
            chart_template_basic = template.copy({'name': 'Basic'})
            chart_template_k2 = template.copy({'name': 'K2'})
            chart_template_k34 = template.copy({'name': 'K34'})
            
            for l in range(0,ws.nrows):
                
                # user type
                if ws.cell_value(l,2) == 1 or ws.cell_value(l,2) in range(10,20) or ws.cell_value(l,2) in range(1000,1999) :
                    user_type = 'account.data_account_type_asset'
                if ws.cell_value(l,2) in range(15,26) or ws.cell_value(l,2) in range(1500,1599) :
                    user_type = 'account.data_account_type_receivable'
                if ws.cell_value(l,2) in range(1900,1999):
                    user_type = 'account.data_account_type_bank'
                if ws.cell_value(l,2) == 1910:
                    user_type = 'account.data_account_type_cash'

                if ws.cell_value(l,2) == 2 or ws.cell_value(l,2) in range(20,30) or ws.cell_value(l,2) in range(2000,2999) :
                        user_type = 'account.data_account_type_liability'
                if ws.cell_value(l,2) == 20 or ws.cell_value(l,2) in range(2000,2050):
                        user_type = 'account.conf_account_type_equity'
                if ws.cell_value(l,2) in [23,24] or ws.cell_value(l,2) in range(2300,2700):
                        user_type = 'account.data_account_type_payable'
                if ws.cell_value(l,2) in [26,27] or ws.cell_value(l,2) in range(2600,2800):
                        user_type = 'account.conf_account_type_tax'
                
                if ws.cell_value(l,2) == 3 or ws.cell_value(l,2) == '30-34'  or ws.cell_value(l,2) in range(30,40) or ws.cell_value(l,2) in range(3000,4000):
                        user_type = 'account.data_account_type_income'
                if ws.cell_value(l,2) in [4,5,6,7] or ws.cell_value(l,2) in ['5-6'] or  ws.cell_value(l,2) in range(30,80) or ws.cell_value(l,2) in ['40-45'] or ws.cell_value(l,2) in range(4000,8000):
                        user_type = 'account.data_account_type_expense'
                
                        
                if ws.cell_value(l,2) == 8 or ws.cell_value(l,2) in [80,81,82,83] or ws.cell_value(l,2) in range(8000,8400):
                        user_type = 'account.data_account_type_income'
                if ws.cell_value(l,2) in [84,88] or ws.cell_value(l,2) in range(8400,8500) or ws.cell_value(l,2) in range(8800,8900):
                        user_type = 'account.data_account_type_expense'
                if ws.cell_value(l,2) in [89] or ws.cell_value(l,2) in range(8900,9000):
                        user_type = 'account.data_account_type_expense'
                        

                


                if ws.cell_value(l,2) in range(1,9) or ws.cell_value(l,2) in ['5-6']: # kontoklass              
                    last_account_class = self.env['account.account.template'].create({
                        'code': ws.cell_value(l,2), 
                        'name': ws.cell_value(l,3), 
                        'user_type': self.env.ref(user_type).id,
                        'type': 'view',
                        'chart_template_id': chart_template_titles.id,
                      })
                if ws.cell_value(l,2) in range(10,99) or ws.cell_value(l,2) in ['30-34','40-45']: # kontogrupp
                    last_account_group = self.env['account.account.template'].create(
                        {
                            'code': ws.cell_value(l,2), 
                            'name': ws.cell_value(l,3), 
                            'type': 'view',
                            'user_type': self.env.ref(user_type).id, 
                            'parent_id':last_account_class.id,
                            'chart_template_id': chart_template_titles.id,
                            })
                
                if ws.cell_value(l,2) in range(1000,9999):
                    if ws.cell_value(l,1) == not_k2 or ws.cell_value(l,4) == not_k2:
                        chart = chart_template_k34.id
                    elif ws.cell_value(l,1) == basic_code or ws.cell_value(l,4) == basic_code:
                        chart = chart_template_basic.id
                    else:
                        chart = chart_template_k2.id
               
                    # tax
                    tax_ids = []
                    if user_type == 'account.data_account_type_income':
                        if  ws.cell_value(l,2) in range(0,0) or ws.cell_value(l,5) in range(0,0):
                            tax_ids = []
                    
                    last_account = self.env['account.account.template'].create({
                        'code': int(ws.cell_value(l,2)) if isinstance( ws.cell_value(l,2), int ) else ws.cell_value(l,2),
                        'name': ws.cell_value(l,3), 
                        'type': 'other', 
                        'parent_id':last_account_group.id,
                        'user_type': self.env.ref(user_type).id,
                        'chart_template_id': chart,
                        'bas_k34': True if  ws.cell_value(l,1) == not_k2 else False,
                        'bas_basic': True if ws.cell_value(l,1) == basic_code else False,
                        })
                    if ws.cell_value(l,5) in range(1000,9999):
                        last_sub_account = self.env['account.account.template'].create({
                            'code':  int(ws.cell_value(l,5)) if isinstance( ws.cell_value(l,5), int ) else ws.cell_value(l,5),
                            'name': ws.cell_value(l,6), 
                            'type': 'other', 
                            'parent_id':last_account.id,
                            'user_type': self.env.ref(user_type).id,
                            'chart_template_id': chart,
                            'bas_k34': True if  ws.cell_value(l,4) == not_k2 else False,
                            'bas_basic': True if ws.cell_value(l,4) == basic_code else False,
                            })
            
            return True
        chart.write({'state': 'get','result': 'All well'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'import.chart.template',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': chart.id,
            'views': [(False, 'form')],
            'target': 'new',
        }


class import_sru_of_account(models.TransientModel):
    _name = 'import.sru.template'

    data = fields.Binary('File')
    @api.one
    def _data(self):
        self.xml_file = self.data
    xml_file = fields.Binary(compute='_data')
    state =  fields.Selection([('choose', 'choose'), ('get', 'get')],default="choose")
    result = fields.Text(string="Result",default='')


   
    @api.multi
    def send_form(self,):
        chart = self[0]
        #raise Warning(chart)
        #_logger.warning('data %s b64 %s ' % (account.data,base64.decodestring(account.data)))
        #~ raise Warning(base64.decodestring(chart.data))
        #~ raise Warning('data %s b64 %s ' % (chart.data.encode('utf-8'),base64.decodestring(chart.data.encode('utf-8'))))
        
#~ def split_domain(txt, c):
    #~ res = []
    #~ for w in txt.split(c):
        #~ res.append(w)
        #~ res.append(c)
    #~ return res[:-1]
    
#~ def get_domain(txt):
    #~ if isinstance(txt, float):
        #~ return None, str(int(txt))
    #~ if txt[0] in ('+', '-'):
        #~ sign = txt[0]
        #~ txt = txt[1:]
    #~ else:
        #~ sign = None
    #~ return sign, txt
    #~ txt = txt.replace(' ', '')
    #~ domain = 

#~ def join_domain(d1, d2):
    #~ return d1 + d2
    #~ for t in d2:
        #~ if t not in d1:
            #~ d1.append(t)

#~ def get_last_heading(l):
    #~ if not l[1] or isinstance(l[1][0], dict):
        #~ return l
    #~ return get_last_heading(l[1][-1])
            
        if not chart.data == None:
            with TemporaryFile('w+') as fileobj:
                fileobj.write(base64.decodestring(chart.data))
                fileobj.seek(0)
                
                wb = open_workbook(file_contents=fileobj.read())
                ws = wb.sheet_by_index(0)

#~ wb = open_workbook('/home/robin/Hämtningar/INK2_16_ver2.xls', formatting_info=True)
#~ ws = wb.sheet_by_index(0)
                
#~ res = []
#~ heading = None
#~ account = None
#~ state = 0

#~ for row in ws.get_rows():
    #~ if state == 0:
        #~ # Looking for start of accounts list
        #~ if row and row[0].value == u'Fält-kod':
            #~ state = 1
    #~ elif state == 1:
        #~ # Looking for new heading or account to process
        #~ if len(row) > 3 and row[0].value:
            #~ print row[0].value
            #~ #Found an account line
            #~ if row[1].value:
                #~ sign, domain = get_domain(row[3].value)
                #~ account = {
                    #~ 'code': row[1].value,
                    #~ 'name': row[2].value,
                    #~ 'domain': domain,
                    #~ 'field_codes': [{
                        #~ 'code': row[0].value,
                        #~ 'sign': sign,
                        #~ 'domain': domain,
                    #~ }]
                #~ }
            #~ else:
                #~ sign, domain = get_domain(row[3].value)
                #~ account['field_codes'].append({
                    #~ 'code': row[0].value,
                    #~ 'sign': sign,
                    #~ 'domain': domain,
                #~ })
                #~ join_domain(account['domain'], domain)
            #~ heading[1].append(account)
        #~ elif len(row) > 2 and row[2].value and row[2].value.upper() == row[2].value:
            #~ #Top level account
            #~ heading = [row[2].value, []]
            #~ res.append(heading)
        #~ elif len(row) > 2 and row[2].value:
            #~ heading = [row[2].value, []]
            #~ get_last_heading(res[-1])[1].append(heading)
                        
                        
                
            #~ raise Warning(ws.cell_value(0,12))
            
            #~ try:
                #~ tools.convert_xml_import(account._cr, 'account_export', fileobj, None, 'init', False, None)
            #~ finally:
            #~ return True
        #~ chart.write({'state': 'get','result': 'All well'})
        #~ return {
            #~ 'type': 'ir.actions.act_window',
            #~ 'res_model': 'import.chart.template',
            #~ 'view_mode': 'form',
            #~ 'view_type': 'form',
            #~ 'res_id': chart.id,
            #~ 'views': [(False, 'form')],
            #~ 'target': 'new',
        #~ }

