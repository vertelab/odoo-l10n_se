# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
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
from odoo import models, fields, api, _, registry
from odoo.exceptions import Warning, RedirectWarning


import csv
import os
import tempfile
import base64


import logging
_logger = logging.getLogger(__name__)


# http://jamesmcdonald.id.au/it-tips/using-gnubarcode-to-generate-a-gs1-128-barcode
# https://github.com/zint/zint

class report_xml(models.Model):
    _inherit = 'ir.actions.report'

    ### Fields
    report_type = fields.Selection(selection_add=[('glabels', 'Glabels')], ondelete={'glabels': 'set default'})
    glabels_template = fields.Binary(string="Glabels template")
    label_count = fields.Integer(string="Count", default=1, help="One if you want to fill the sheet with new records, the count of labels of the sheet to fill each sheet with one record")

#     def _lookup_report(self, name):
#         if 'report.' + name in interface.report_int._reports:
#             new_report = interface.report_int._reports['report.' + name]
#         else:
#             self.env.cr.execute("SELECT id, report_type,  \
#                         model, glabels_template, label_count  \
#                         FROM ir_act_report_xml \
#                         WHERE report_name=%s", (name,))
#             record = self.env.cr.dictfetchone()
#             if record['report_type'] == 'glabels':
#                 template = base64.b64decode(record['glabels_template']) if record['glabels_template'] else ''
#                 new_report = glabels_report( 'report.%s'%name, record['model'], template=template, count=record['label_count'])
#             else:
#                 new_report = super(report_xml, self)._lookup_report( name)
#         return new_report
#
#
# class glabels_report(object):
#
#     def __init__(self, cr, name, model, template=None,count=1 ):
#         _logger.info("registering %s (%s)" % (name, model))
#         self.active_prints = {}
#
#         pool = registry(cr.dbname)
#         ir_obj = pool.get('ir.actions.report.xml')
#         name = name.startswith('report.') and name[7:] or name
#         self.template = template
#         self.model = model
#         self.count = count
#         try:
#             report_xml_ids = ir_obj.search(cr, 1, [('report_name', '=', name)])
#             if report_xml_ids:
#                 report_xml = ir_obj.browse(cr, 1, report_xml_ids[0])
#             else:
#                 report_xml = False
#         except Exception as e:
#             _logger.error("Error while registering report '%s' (%s)", name, model, exc_info=True)
#
#
#     def create(self, cr, uid, ids, data, context=None):
#
#         temp = tempfile.NamedTemporaryFile(mode='w+t',suffix='.csv')
#         outfile = tempfile.NamedTemporaryFile(mode='w+b',suffix='.pdf')
#         glabels = tempfile.NamedTemporaryFile(mode='w+t',suffix='.glabels')
#         glabels.write(base64.b64decode(data.get('template')) if data.get('template') else None or self.template)
#         glabels.seek(0)
#
#         pool = registry(cr.dbname)
#         labelwriter = None
#         for p in pool.get(self.model).read(cr,uid,ids):
#             if not labelwriter:
#                 labelwriter = csv.DictWriter(temp,p.keys())
#                 labelwriter.writeheader()
#             for c in range(self.count):
#                 labelwriter.writerow({k:isinstance(v, (str, unicode)) and v.encode('utf8') or v for k,v in p.items()})
#         temp.seek(0)
#         res = os.system("glabels-3-batch -o %s -l -C -i %s %s" % (outfile.name,temp.name,glabels.name))
#         outfile.seek(0)
#         pdf = outfile.read()
#         outfile.close()
#         temp.close()
#         glabels.close()
#         return (pdf,'pdf')
