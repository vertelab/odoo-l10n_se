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


import logging
_logger = logging.getLogger(__name__)

class account_export(models.TransientModel):
    _name = 'account.export'
    _description = 'Records for exports'
    _order = 'name'

    data = fields.Binary('File')
    @api.one
    def _data(self):
        self.xml_file = self.data
    xml_file = fields.Binary(compute='_data')
    def _periods(self):
        return [p.id for p in self.env['account.period'].search([])]
    period_ids = fields.Many2many('account.period',default=_periods)
    description = fields.Text('Note', help="This will be included in the message")
    state =  fields.Selection([('choose', 'choose'), ('get', 'get')],default="choose") 
    depth =  fields.Selection([('0', 'none'), ('1', '1 level'), ('2', '2 levels'), ('3', '3 levels'), ('4', '4 levels')],default="0") 
    name = fields.Char('File Name', readonly=True)
    #model = fields.Selection([('res.partner','Customers'),('account.invoice','Invoices'),('account.move','Moves')],string="Model")
    model = fields.Many2one(comodel_name='ir.model',string="Model")
    model_ids = fields.Many2many(comodel_name="ir.model")

    has_period = fields.Boolean('Has Period')

    @api.returns('ir.model')
    def _get_models(self,model,depth,maxdepth=4):
        models = set()        
        #_logger.info('Get related model  %s ' % (model.fields_get()))
        _logger.info('Get related model items %s ' % (self.env[model.model].fields_get().items()))
        #_logger.info('Get related model iteritems %s ' % (model.fields_get().iteritems()))
        if depth <= maxdepth:
            for field,values in self.env[model.model].fields_get().items():
                _logger.info('field %s values %s ' % (field,values.get('relation')))
                if values.get('relation',False) != False:
                    _logger.info('field %s type %s relation %s före' % (field,values['type'],values.get('relation')))                    
                    if field not in ['create_date','id','write_date','create_uid','__last_update','write_uid','inherited_model_ids','view_ids','field_id','access_ids']:
                        _logger.info('field %s type %s relation %s' % (field,values['type'],values.get('relation')))
                        models.add(self.env['ir.model'].search([('model','=',values.get('relation'))]))
                        depth += 1
                        _logger.warning('Depth %s Max %s' % (depth,maxdepth))
                        self._get_models(self.env['ir.model'].search([('model','=',values.get('relation'))]),depth,maxdepth)
                _logger.info('models %s' % (list(models)))
            #raise Exception("The record has been deleted or not %s" % models)
        return list(models)

   
    @api.onchange('model','depth')
    def _onchange_model(self):
        self.has_period = self.model and 'period_id' in self.env[self.model.model].fields_get()
        if self.model and self.model.model:
            self.model_ids = [m.id for m in self._get_models(self.model,1,maxdepth=int(self.depth))] 
 
        #self.model_ids  all related models with this depth

   
   
    @api.multi
    def send_form(self,):
        account = self[0]
        #_logger.warning('data %s b64 %s ' % (account.data,base64.decodestring(account.data)))
        if not account.data == None:
            fileobj = TemporaryFile('w+')
            fileobj.write(base64.decodestring(account.data))
            fileobj.seek(0)
            try:
                tools.convert_xml_import(account._cr, 'account_export', fileobj, None, 'init', False, None)
            finally:
                fileobj.close()
            return True
        account.write({'state': 'get', 'name': '%s.xml' % account.model.model.replace('.','_'),'data': base64.b64encode(account._export_xml()) })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.export',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': account.id,
            'views': [(False, 'form')],
            'target': 'new',
        }


    def get_records(self,model):
        if 'period_id' in self.env[self.model.model].fields_get():
            return self.env[self.model.model].search(['period_id','in',self.period_ids])
        else:
            return self.env[self.model.model].search([])


    @api.model
    def _export_xml(self):
        """
            models : a list of recordsets to export
   
            returns an xml-document as binary (string)
        """
        def _external_id(record):
            ext_id = record.get_external_id()[record.id]
            if not ext_id:
                ext_id = '%s-%s-%s' % (record._name.replace('.','_'),self.env['ir.config_parameter'].get_param('database.uuid'),record.id)
                #~ if 'code' in record.fields_get().keys():
                    #~ ext_id =  '%s' % record.code
                #~ elif 'number' in record.fields_get().keys():
                    #~ ext_id =  '%s' % record.number
                #~ elif 'internal_number' in record.fields_get().keys():
                    #~ ext_id = '%s' %  record.internal_number
                #~ elif 'record_name' in record.fields_get().keys():
                    #~ ext_id = '%s' %  record.record_name
                #~ else:
                    #~ ext_id = '%s' % record.name
                module = record._original_module
                _logger.debug("%s: Generating new external ID `%s.%s` for %r.", self._name, module, ext_id, record)
                self.env['ir.model.data'].sudo().create({'name': ext_id,
                                                        'model': record._name,
                                                        'module': module,
                                                        'res_id': record.id})
                ext_id = "%s.%s" % (module,ext_id)
            return ext_id

            

        def export_xml(recordsets):
            document = etree.Element('openerp')
            data = etree.SubElement(document,'data')
            for lines in recordsets:
                for line in lines:
                    if line.id:
                        ext_id = _external_id(line)
                        _logger.info("Reporting Block id = %s" % ext_id)          
                        record = etree.SubElement(data,'record',id=ext_id,model=line._name)
                        names = [name for name in line.fields_get().keys() if fnmatch(name,'in_group*')] + [name for name in line.fields_get().keys() if fnmatch(name,'sel_groups*')]
                        for field,values in line.fields_get().items():
                            if not field in ['create_date','nessage_ids','id','write_date','create_uid','__last_update','write_uid',] + names:
                                if values.get('type') in ['boolean','char','text','float','integer','selection','date','datetime']:
                                    _logger.info("Simple field %s field %s values %s" % (values.get('type'),field,values))
                                    try:
                                    #if eval('line.%s' % field):
                                        #~ etree.SubElement(record,'field',name = field).text = "%s" % eval('line.%s' % field) or ""
                                        etree.SubElement(record,'field',name = field).text = "%s" % eval('line.%s' % field)
                                    except:
                                        pass
                                elif values.get('type') in ['many2one']:
                                    if eval('line.%s' % field):                                     
                                        etree.SubElement(record,'field',name=field,ref="%s" % eval('_external_id(line.%s)' % field))
                                elif values.get('type') in ['one2many']:  # Update from the other end
                                    pass
                                elif values.get('type') in ['many2many']: # TODO
                                        # <field name="member_ids" eval="[(4, ref('base.user_root')),(4, ref('base.user_demo'))]"/>
                                    m2mvalues = []
                                    for val in line:
                                        external_id = _external_id(val)
                                        _logger.info("External id %s -> %s" % (id,external_id))
                                        m2mvalues.append("(4, ref('%s'))" % external_id)
            #                            m2mvalues.append("(4, ref('%s'))" % val.get_external_id().items()[0] or '')
                                    if len(m2mvalues)>0:
                                        etree.SubElement(record,'field',name=field,eval="[%s]" % (','.join(m2mvalues)))                 

            return document

        if 'period_id' in self.env[self.model.model].fields_get().keys():
            records = self.env[self.model.model].search(['period_id','in',[p.id for p in self.period_ids]])
        else:
            records = self.env[self.model.model].search([])

        supporting_records = set()
        for r in records:
            for f,a in r.fields_get().items():
                if a.get('relation') and a.get('relation') in [m.model for m in self.model_ids]:
                    if eval('r.%s' % f):
                        supporting_records.add(eval('r.%s' % f))
                
        _logger.warning("Supporting = %s" % supporting_records)  
        
        return etree.tostring(export_xml(list(supporting_records) + list(records)),pretty_print=True,encoding="utf-8")
