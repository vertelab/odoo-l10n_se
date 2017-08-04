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

    data_normal = fields.Binary('BAS Normal')
    data_simplified = fields.Binary('BAS K1 simplified')
   
    @api.multi
    def send_form(self,):
        chart = self[0]
        #_logger.warning('data %s b64 %s ' % (account.data,base64.decodestring(account.data)))
        #~ raise Warning('data %s b64 %s ' % (chart.data.encode('utf-8'),base64.decodestring(chart.data.encode('utf-8'))))
        
        if not chart.data_normal == None:
            
            wb = open_workbook(file_contents=base64.decodestring(chart.data_normal))
            #~ wb = open_workbook(file_contents=chart.data)
            ws = wb.sheet_by_index(0)
            basic_code = u' \u25a0'
            not_k2 = u'[Ej K2]'
                
            #raise Warning(ws.row_len(4),len(ws.cell_value(0,1)),ws.cell_value(0,1))
            if  ws.cell_value(0,1)[:41] == u"BAS Förenklat årsbokslut (K1) – Kontoplan":
                self.chart_simplified(ws)
                #~ raise Warning('K1 kontoplan')
            elif ws.cell_value(0,1)[:47] == u'BAS Förenklat årsbokslut (K1) – Minimikontoplan':
                self.chart_mini(ws)
                raise Warning('K1 mini')
            elif ws.row_len(4) > 3 and ws.cell_value(3,3) == u'Huvudkonton ':
                chart.chart_normal(ws) # raise Warning('Normalplan K2-K4')
            else:
                raise Warning('Unknown format')

        if not chart.data_simplified == None:
            
            wb = open_workbook(file_contents=base64.decodestring(chart.data_simplified))
            #~ wb = open_workbook(file_contents=chart.data)
            ws = wb.sheet_by_index(0)
            basic_code = u' \u25a0'
            not_k2 = u'[Ej K2]'
                
            #raise Warning(ws.row_len(4),len(ws.cell_value(0,1)),ws.cell_value(0,1))
            if  ws.cell_value(0,1)[:41] == u"BAS Förenklat årsbokslut (K1) – Kontoplan":
                self.chart_simplified(ws)
                #~ raise Warning('K1 kontoplan')
            elif ws.cell_value(0,1)[:47] == u'BAS Förenklat årsbokslut (K1) – Minimikontoplan':
                self.chart_mini(ws)
                raise Warning('K1 mini')
            elif ws.row_len(4) > 3 and ws.cell_value(3,3) == u'Huvudkonton ':
                chart.chart_normal(ws) # raise Warning('Normalplan K2-K4')
            else:
                raise Warning('Unknown format')


    def chart_title(self,code,name,last_account_class):
            last_account_group = None
            chart_template_titles = self.env['account.chart.template'].search([('name','=','Title')])
            if not chart_template_titles:
                chart_template_titles = self.env['account.chart.template'].search([])[-1].copy({'name': 'Title'})
            else:
                chart_template_titles = chart_template_titles[-1]
    
            root_account = self.env['account.account.template'].search([('name','=','root normal')])
            if not root_account:
                root_account = self.env['account.account.template'].create({
                        'code': 'root normal',
                        'name': 'root normal', 
                        'user_type': self.env.ref('account.data_account_type_asset').id,
                        'type': 'view',
                        'chart_template_id': chart_template_titles.id,
                      })    
    
            #~ (c,t) = code.split() if isinstance(code, basestring) else (None,None)
            _logger.warn('>>>>>>>>>>%s  | %s' % (code.split() if isinstance(code, basestring) else None,type(code)))
            if isinstance(code, basestring) and len(code) > 0 and ord(code[0]) in range(ord('0'),ord('9')):
                name = ' '.join(code.split()[1:])
                code = code if code.split()[0] in ['5-6','30-34','40-45',u'30\u201334',u'40\u2013',u'5\u20136'] else int(code.split()[0]) 
            #~ if isinstance(c, float) and int(c) in range(10,100):
                #~ raise Warning(c,t)
            if code in range(1,9) or code in [u'5–6']: # kontoklass              
                last_account_class = self.env['account.account.template'].create({
                    'code': str(int(code)) if isinstance(code, float ) else code, 
                    'name': name, 
                    'user_type': self.env['account.account.type'].account2user_type(code).id,
                    'type': 'view',
                    'chart_template_id': chart_template_titles.id,
                    'parent_id':root_account.id,
                  })
            if code in range(10,99) or code in [u'30–34 Huvudintäkter',u"""40–
45 """]: # kontogrupp
                last_account_group = self.env['account.account.template'].create({
                        'code': str(int(code)) if isinstance( code, float ) else code, 
                        'name': name, 
                        'type': 'view',
                        'user_type': self.env['account.account.type'].account2user_type(code).id, 
                        'parent_id':last_account_class.id,
                        'chart_template_id': chart_template_titles.id,
                    })
            return (last_account_class,last_account_group,root_account)            
            
    def chart_normal(self,ws):

        basic_code = u' \u25a0'
        not_k2 = u'[Ej K2]'
    
        nbr_lines = ws.nrows
                
        chart_template_titles = self.env.ref('l10n_se.chart_title')
        chart_template_simplified = self.env.ref('l10n_se.chart_simplified')
        chart_template_basic = self.env.ref('l10n_se.chart_basic')
        chart_template_k2 = self.env.ref('l10n_se.chart_k2')
        chart_template_k34 = self.env.ref('l10n_se.chart_k34')
        
        last_account_class = None
        
        for l in range(0,ws.nrows):
        
            (last_account_class,last_account_group,root_account)  =  self.chart_title(ws.cell_value(l,2),ws.cell_value(l,3),last_account_class)
        
            #~ if ws.cell_value(l,2) in range(1,9) or ws.cell_value(l,2) in [u'5–6']: # kontoklass              
                #~ last_account_class = self.env['account.account.template'].create({
                    #~ 'code': str(int(ws.cell_value(l,2))) if isinstance( ws.cell_value(l,2), float ) else ws.cell_value(l,2), 
                    #~ 'name': ws.cell_value(l,3), 
                    #~ 'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,2)).id,
                    #~ 'type': 'view',
                    #~ 'chart_template_id': chart_template_titles.id,
                    #~ 'parent_id':root_account.id,
                  #~ })
            #~ if ws.cell_value(l,2) in range(10,99) or ws.cell_value(l,2) in [u'30–34 Huvudintäkter',u"""40–
#~ 45 """]: # kontogrupp
                #~ last_account_group = self.env['account.account.template'].create({
                        #~ 'code': str(int(ws.cell_value(l,2))) if isinstance( ws.cell_value(l,2), float ) else ws.cell_value(l,2), 
                        #~ 'name': ws.cell_value(l,3), 
                        #~ 'type': 'view',
                        #~ 'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,2)).id, 
                        #~ 'parent_id':last_account_class.id,
                        #~ 'chart_template_id': chart_template_titles.id,
                    #~ })
            
            if ws.cell_value(l,2) in range(1000,9999):
                
                reconcile = ws.cell_value(l,2) in range(1900,2000) or ws.cell_value(l,2) in [1630] or ws.cell_value(l,5) in range(1900,2000) or ws.cell_value(l,5) in [1630]
                
                if ws.cell_value(l,1) == not_k2 or ws.cell_value(l,4) == not_k2:
                    chart = chart_template_k34.id
                elif ws.cell_value(l,1) == basic_code or ws.cell_value(l,4) == basic_code:
                    chart = chart_template_basic.id
                else:
                    chart = chart_template_k2.id
           
                last_account = self.create_account(ws.cell_value(l,2),ws.cell_value(l,3),None,chart)           
                #~ last_account = self.env['account.account.template'].create({
                    #~ 'code': int(ws.cell_value(l,2)) if isinstance( ws.cell_value(l,2), int ) else str(int(ws.cell_value(l,2))),
                    #~ 'name': ws.cell_value(l,3), 
                    #~ 'type': 'other', 
                    #~ 'parent_id':last_account_group.id if last_account_group else None,
                    #~ 'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,2)).id,
                    #~ 'chart_template_id': chart,
                    #~ 'bas_k34': True if  ws.cell_value(l,1) == not_k2 else False,
                    #~ 'bas_basic': True if ws.cell_value(l,1) == basic_code else False,
                    #~ 'tax_ids': self.env['account.tax.template'].account2tax_ids(ws.cell_value(l,2)),
                    #~ 'reconcile': reconcile,
                    #~ })
                if ws.cell_value(l,5) in range(1000,9999):
                    last_sub_account = self.create_account(ws.cell_value(l,5),ws.cell_value(l,6),last_account,chart)
                    #~ last_sub_account = self.env['account.account.template'].create({
                        #~ 'code':  int(ws.cell_value(l,5)) if isinstance( ws.cell_value(l,5), int ) else str(int(ws.cell_value(l,5))),
                        #~ 'name': ws.cell_value(l,6), 
                        #~ 'type': 'other', 
                        #~ 'parent_id':last_account.id,
                        #~ 'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,5)).id,
                        #~ 'chart_template_id': chart,
                        #~ 'bas_k34': True if  ws.cell_value(l,4) == not_k2 else False,
                        #~ 'bas_basic': True if ws.cell_value(l,4) == basic_code else False,
                        #~ 'tax_ids': self.env['account.tax.template'].account2tax_ids(ws.cell_value(l,5)),
                        #~ 'reconcile': reconcile,
                        #~ })
        
        return True

    def create_account(self,code,name,parent_id,chart,overwrite=False):
        account = self.env['account.account.template'].search([('code','=',code)])
        if len(account)>0:
            account = account[0]
        if account and overwrite and parent_id == None:
            account.chart_template_id = chart
            return account
        else:
            return self.env['account.account.template'].create({
                'code': int(code) if isinstance( code, int ) else str(int(code)),
                'name': name, 
                'type': 'other', 
                'parent_id':parent_id,
                'user_type': self.env['account.account.type'].account2user_type(code).id,
                'chart_template_id': chart,
                'tax_ids': self.env['account.tax.template'].account2tax_ids(code),
                #~ 'reconcile': True if code in range(1900,2000) + [1630] else False,
                'reconcile': False,
                })

    def chart_simplified(self,ws):
        chart = self.env.ref('l10n_se.chart_simplified')
        last_account_class = None
        for l in range(0,ws.nrows):
            _logger.warn(ws.cell_value(l,1))
            
            (last_account_class,last_account_group,root_account)  =  self.chart_title(ws.cell_value(l,1),ws.cell_value(l,2),last_account_class)

            if ws.cell_value(l,1) in range(1000,9999):

                last_account = self.create_account(ws.cell_value(l,1),ws.cell_value(l,2),None,chart.id,owerwrite=True)

                #~ last_account = self.env['account.account.template'].create({
                    #~ 'code': int(ws.cell_value(l,1)) if isinstance( ws.cell_value(l,1), int ) else str(int(ws.cell_value(l,1))),
                    #~ 'name': ws.cell_value(l,2), 
                    #~ 'type': 'other', 
                    #~ 'parent_id':None,
                    #~ 'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,1)).id,
                    #~ 'chart_template_id': chart.id,
                    #~ 'tax_ids': self.env['account.tax.template'].account2tax_ids(ws.cell_value(l,1)),
                    #~ 'reconcile': False,
                    #~ })
                if ws.cell_value(l,4) in range(1000,9999):
                    last_sub_account = self.create_account(ws.cell_value(l,4),ws.cell_value(l,5),last_account.id,chart.id,owerwrite=True)

                    #~ last_sub_account = self.env['account.account.template'].create({
                        #~ 'code':  int(ws.cell_value(l,4)) if isinstance( ws.cell_value(l,4), int ) else str(int(ws.cell_value(l,4))),
                        #~ 'name': ws.cell_value(l,5), 
                        #~ 'type': 'other', 
                        #~ 'parent_id':last_account.id,
                        #~ 'user_type': self.env['account.account.type'].account2user_type(ws.cell_value(l,4)).id,
                        #~ 'chart_template_id': chart.id,
                        #~ 'tax_ids': self.env['account.tax.template'].account2tax_ids(ws.cell_value(l,4)),
                        #~ 'reconcile': False,
                        #~ })
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

class AccountSRUCode(models.Model):
    _name = 'account.sru.code'
    
    name = fields.Char(string='Name')
    field_code = fields.Char('Field Code')

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

        def join_domain(d1, d2):
            """Join two domains."""
            return d1 + d2
            for t in d2:
                if t not in d1:
                    d1.append(t)

        def parse_domain(dl):
            """Parse a list representing a BAS string."""
            #~ print '0 %s' % dl
            if not dl:
                return []
            changed = True
            while changed:
                changed = False
                for i in range(0, len(dl)):
                    if dl[i] == '(':
                        for j in range(i + 1, len(dl)):
                            if dl[j] == ')':
                                dl = dl[:i] + [parse_domain(dl[i + 1 : j])] + dl[j + 1:]
                                changed = True
                                break
                        break
            #~ print '1 %s' % dl
            #Handle spans (189x - 1930). Can contain wildcards for some mysterious reason.
            changed = True
            while changed:
                changed = False
                for i in range(0, len(dl)):
                    if dl[i] == '-':
                        dl = dl[:i - 1] [[str(x) for x in range(int(dl[i - 1].replace('x', '0')), int(dl[i + 1].replace('x', '9')) + 1)]] + dl[i + 2:]
                        changed = True
                        break
            #~ print '2 %s' % dl
            # Handle numbers, wildcards and commas
            for i in range(0, len(dl)):
                if isinstance(dl[i], list) or dl[i] == '!':
                    pass
                    #~ print '2.0 %s' % dl
                elif dl[i] == ',':
                    dl[i] = []
                    #~ print '2.1 %s' % dl
                elif dl[i].isdigit():
                    dl[i] = [dl[i]]
                    #~ print '2.2 %s' % dl
                else:
                    dl[i] = [str(x) for x in range(int(dl[i].replace('x', '0')), int(dl[i].replace('x', '9')) + 1)]
                    #~ print '2.3 %s' % dl
            #~ print '3 %s' % dl
            # Handle not
            ignore_ids = []
            changed = True
            while changed:
                changed = False
                for i in range(0, len(dl)):
                    if dl[i] == '!':
                        ignore_ids += dl.pop(i + 1)
                        dl.pop(i)
                        changed = True
                        break
            #~ print '4 %s' % dl
            # Build id list
            ids = []
            for e in dl:
                for id in e:
                    if id not in ignore_ids:
                        ids.append(id)
            return ids
            
        def get_domain(txt):
            """Get a domain from a BAS string."""
            if isinstance(txt, float):
                return None, [('code', '=', str(int(txt)))]
            txt = txt.replace(' ', '')  
            if txt[0] in ('+', '-'):
                sign = txt[0]
                txt = txt[1:]
            else:
                sign = None
            txt = txt.replace('exkl.', '!')
            separators = ',-()!'
            for sep in separators:
                txt = txt.replace(sep, ' %s ' % sep)
            return sign, [('code', 'in', parse_domain(txt.split()))]

            res = []
            with TemporaryFile('w+') as fileobj:
                fileobj.write(base64.decodestring(self.data))
                fileobj.seek(0)
                wb = open_workbook(file_contents=fileobj.read(), formatting_info=True)
                ws = wb.sheet_by_index(0)
                heading = None
                account = None
                state = 0
                for row in ws.get_rows():
                    #~ print row
                    if state == 0:
                        #Looking for start of accounts list
                        if row and row[0].value == u'Fält-kod':
                            state = 1
                    elif state == 1:
                        # Looking for new heading or account to process
                        if len(row) > 3 and row[0].value:
                            #Found an account row.
                            if row[1].value:
                                #This row has an SRU code.
                                sign, domain = get_domain(row[3].value)
                                account = {
                                    'code': row[1].value,
                                    'name': row[2].value,
                                    'domain': domain,
                                    'field_codes': [{
                                        'code': int(row[0].value),
                                        'sign': sign,
                                        'domain': domain,
                                    }]
                                }
                            else:
                                #No SRU code on this row. Shares SRU with previous row.
                                sign, domain = get_domain(row[3].value)
                                account['field_codes'].append({
                                    'code': int(row[0].value),
                                    'sign': sign,
                                    'domain': domain,
                                })
                                join_domain(account['domain'], domain)
                            heading['accounts'].append(account)
                        elif len(row) > 2 and row[2].value and row[2].value.isupper():
                            #Top level heading
                            heading = {
                                'name': row[2].value,
                                'accounts': [],
                                'children': [],
                                'height': wb.font_list[wb.xf_list[row[2].xf_index].font_index].height,
                                'parent': None,
                            }
                            res.append(heading)
                        elif len(row) > 2 and row[2].value:
                            #Subheading
                            h = heading
                            height = wb.font_list[wb.xf_list[row[2].xf_index].font_index].height
                            #~ print height
                            while True:
                                #~ print 'h: %s' % h['name']
                                if not h['parent']:
                                    break
                                if h['height'] > height:
                                    break
                                h = h['parent']
                            heading = {
                                'name': row[2].value,
                                'accounts': [],
                                'children': [],
                                'height': height,
                                'parent': h,
                            }
                            h['children'].append(heading)


