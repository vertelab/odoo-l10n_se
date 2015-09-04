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
    period_ids = fields.Many2many('account.period',)
    description = fields.Text('Note', help="This will be included in the message")
    state =  fields.Selection([('choose', 'choose'), ('get', 'get')],default="choose") 
    depth =  fields.Selection([('0', 'none'), ('1', '1 level'), ('2', '2 levels'), ('3', '3 levels'), ('4', '4 levels')],default="0") 
    name = fields.Char('File Name', readonly=True)
    model = fields.Selection([('res.partner','Customers'),('account.invoice','Invoices'),('account.move','Moves')],string="Model")
    #model = fields.Many2one(comodel_name='res.model',string="Model")
    #models_ids 

    has_period = fields.Boolean('Has Period')
   
    @api.onchange('model')
    def _onchange_model(self):
        self.has_period = self.model and 'period_id' in self.env[self.model].fields_get()
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
        if len(account.period_ids)>0 and 'period_id' in self.env[account.model].fields_get():
            data = base64.b64encode(account._export_xml(self.env[account.model].search([('period_id','in',[p.id for p in self.period_ids])]),int(account.depth)))
        else:
            data = base64.b64encode(self._export_xml(self.env[account.model].search([]),int(account.depth)))
        account.write({'state': 'get', 'name': '%s.xml' % account.model.replace('.','_'),'data': data })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.export',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': account.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    @api.model
    def _export_xml(self,models,maxdepth):
        """
            models : a list of recordsets to export
            maxdepth : how extensive the search for related records shall bee
   
            returns an xml-document as binary (string)
        """
        def _external_id(record):
            ext_id = record.get_external_id()[record.id]
            if not ext_id:
                ext_id = '%s-%s-%s' % (record._name.replace('.','_'),self.env['ir.config_parameter'].get_param('database.uuid'),record.id)
                module = record._original_module
                _logger.debug("%s: Generating new external ID `%s.%s` for %r.", self._name, module, ext_id, record)
                self.env['ir.model.data'].sudo().create({'name': ext_id,
                                                        'model': record._name,
                                                        'module': module,
                                                        'res_id': record.id})
            else:
                module, ext_id = ext_id.split('.')
            return '%s.%s' % (module, ext_id)


        def export_xml(lines):
            document = etree.Element('openerp')
            data = etree.SubElement(document,'data')
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

        def get_related(models,depth,maxdepth=4):
            objects = set()
            if depth < maxdepth:
                for model in models:
                    # get_related within choosen model_ids
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

        #_logger.info("models %s depth %s" % (models,maxdepth))   
        if maxdepth == 0:
            return etree.tostring(export_xml(models),pretty_print=True,encoding="utf-8")
        else:
            return etree.tostring(export_xml(get_related(models,maxdepth)),pretty_print=True,encoding="utf-8")
            

    
