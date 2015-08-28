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

import logging
_logger = logging.getLogger(__name__)

class account_export(models.Model):
    _name = 'account.export'
    _description = 'Records for exports'
    _order = 'name'

    name = fields.Char('Export',required=True,help="")
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.tax.esdk'))
    state = fields.Selection([('draft','Open'), ('done','Closed')], 'Status', default='draft',readonly=False, copy=False)
    period_start = fields.Many2one('account.period', string='Start Period',
        domain=[('state', '!=', 'done')], copy=False,
        help="Starting period for the file",
        readonly=True, states={'draft': [('readonly', False)]})
    period_end = fields.Many2one('account.period', string='End Period',
        domain=[('state', '!=', 'done')], copy=False,
        help="Ending pediod for the file, can be same as start period",
        readonly=True, states={'draft': [('readonly', False)]})
        
    @api.one
    def _perdiod_ids(self):
        self.period_ids = self.env['account.period']
        self.period_ids = self.move_id.line_id.filtered(lambda p: p.date_start >= self.period_start.date_start and p.date_stop <= self.period_end.date_stop)

    #period_ids = fields.Many2many('account.period',compute='_period_ids',readonly=True)
    description = fields.Text('Note', help="This will be included in the message")

    @api.model
    def get_tax_sum(self,code):
        account_tax = self.env['account.tax'].search([('description','=',code)])
        if not account_tax or len(account_tax) == 0:
            return _("Error in code %s" % code)
        #_logger.warning("This is tax  %s / %s" % (self.env['account.tax.code'].browse(account_tax.tax_code_id.id).name,code))
        #~ return self.env['account.tax.code'].with_context(
                    #~ {'period_id': self.period_start.id,
                     #~ 'state': 'all'}
                #~ ).browse(account_tax.tax_code_id.id).sum_period or 0
        return self.env['account.tax.code'].with_context(
                    {'period_ids': [p.id for p in self.env['account.period'].search([('date_start', '>=', self.period_start.date_start), ('date_stop', '<=', self.period_end.date_stop)])],
                     'state': 'all'}
                ).browse(account_tax.tax_code_id.id).sum_periods or 0

    @api.one
    def customers_xml(self,):
        self.env['ir.attachment'].create({
            'name':  'Moms%s.xml' % self.name,
            'datas_fname': 'Moms%s.xml' % self.name,
            'res_model': self._name,
            'res_id': self.id,
            'datas':  base64.b64encode(self.pool.get('ir.ui.view').render(self._cr,self._uid,'l10n_se_esdk.esdk_period_moms',values={'doc': self})),
        })

    @api.one
    def invoices_xml(self,):
        self.env['ir.attachment'].create({
            'name':  'Ag%s.xml' % self.name,
            'datas_fname': 'Ag%s.xml' % self.name,
            'res_model': self._name,
            'res_id': self.id,
            'datas':  base64.b64encode(self.pool.get('ir.ui.view').render(self._cr,self._uid,'l10n_se_esdk.esdk_period_ag',values={'doc': self})),
        })

    @api.one
    def moves_xml(self,):
        self.env['ir.attachment'].create({
            'name':  'Ag%s.xml' % self.name,
            'datas_fname': 'Ag%s.xml' % self.name,
            'res_model': self._name,
            'res_id': self.id,
            'datas':  base64.b64encode(self.pool.get('ir.ui.view').render(self._cr,self._uid,'l10n_se_esdk.esdk_period_ag',values={'doc': self})),
        })

    @api.model
    def _export_xml(self,models,maxdepth):
        """
            models : a list of recordsets to export
            maxdepth : how extensive the search for related records shall bee
   
            returns an xml-document as binary (string)
        """
        def export_xml(lines):
            document = etree.Element('openerp')
            data = etree.SubElement(document,'data')
            for line in lines:
                if line.id:
                    k,id = line.get_external_id().items()[0] if line.get_external_id() else 0,"%s-%s" % (line._name,line.id)
                    _logger.info("Reporting Block id = %s" % id)          
                    record = etree.SubElement(data,'record',id=id,model=line._name)
                    names = [name for name in line.fields_get().keys() if fnmatch(name,'in_group*')] + [name for name in line.fields_get().keys() if fnmatch(name,'sel_groups*')]
                    for field,values in line.fields_get().items():
                        if not field in ['create_date','nessage_ids','id','write_date','create_uid','__last_update','write_uid',] + names:
                            if values.get('type') in ['boolean','char','text','float','integer','selection','date','datetime']:
                                _logger.info("Simple field %s field %s values %s" % (values.get('type'),field,values))
                                try:
                                #if eval('line.%s' % field):
                                    etree.SubElement(record,'field',name = field).text = "%s" % eval('line.%s' % field)
                                except:
                                    pass
                            elif values.get('type') in ['many2one']:
                                if eval('line.%s' % field):                                     
                                    k,id = eval('line.%s.get_external_id().items()[0]' % field) if eval('line.%s.get_external_id()' % field) else (0,"%s-%s" % (eval('line.%s._name' % field),eval('line.%s.id' % field)))
                                    if id == "":
                                        id = "%s-%s" % (eval('line.%s._name' % field),eval('line.%s.id' % field))
                                    etree.SubElement(record,'field',name=field,ref="%s" % id)
                            elif values.get('type') in ['one2many']:  # Update from the other end
                                pass
                            elif values.get('type') in ['many2many']: # TODO
                                    # <field name="member_ids" eval="[(4, ref('base.user_root')),(4, ref('base.user_demo'))]"/>
                                m2mvalues = []
                                for val in line:
                                    id,external_id = 0,'' if not val.get_external_id() else val.get_external_id().items()[0]
                                    _logger.info("External id %s -> %s" % (id,external_id[1]))
                                    if len(external_id)>0:
                                        m2mvalues.append("(4, ref('%s'))" % external_id[1])
        #                            m2mvalues.append("(4, ref('%s'))" % val.get_external_id().items()[0] or '')
                                if len(m2mvalues)>0:
                                    etree.SubElement(record,'field',name=field,eval="[%s]" % (','.join(m2mvalues)))                 
                 
            return document

        def get_related(models,depth,maxdepth=4):
            objects = set()
            if depth < maxdepth:
                for model in models:
                    _logger.info('Get related model %s id %s' % (model._name,model.id))
                    for field,values in model.fields_get().items(): 
                        if not field in ['create_date','nessage_ids','id','write_date','create_uid','__last_update','write_uid']:
                            if values.get('type') in ['many2one']:
                                for related in get_related(eval("model.%s" % field),depth+1):
                                    objects.add(related)
                            if values.get('type') in ['many2many']:
                                for related in get_related(eval("model.%s" % field),depth+1):
                                    objects.add(related)
                    objects.add(model)
            return list(objects)

        return etree.tostring(export_xml(get_related(models,0)),pretty_print=True,encoding="utf-8")
