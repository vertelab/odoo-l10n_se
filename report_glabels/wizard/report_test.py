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

from odoo import models, fields, api, _
from odoo.exceptions import Warning
import re


class report_print_by_action(models.TransientModel):
    _name = 'report_glabel.print_by_action'
    
    def to_print(recs):
        valid_input = re.match('^\s*\[?\s*((\d+)(\s*,\s*\d+)*)\s*\]?\s*$', recs[0].object_ids)
        valid_input = valid_input and valid_input.group(1) or False
        if not valid_input:
            raise Warning(_("Input single record ID or number of comma separated IDs!"))
        print_ids = eval("[%s]" % valid_input, {})
        rep_obj = recs.env['ir.actions.report']
        report = rep_obj.browse(recs.env.context['active_ids'])[0]
        data = {
                'model': report.model,
                'ids': print_ids,
                'id': print_ids[0],
                'template': recs[0].template,
                'report_type': 'glabels'
                }
        res = {
                'type': 'ir.actions.report',
                'report_name': report.report_name,
                'datas': data,
                'context': recs.env.context
                }
        return res
    
    ### Fields
    name = fields.Text('Object Model', readonly=True)
    object_ids = fields.Char('Object IDs', size=250, required=True,
        help="Single ID or number of comma separated record IDs")
    template = fields.Binary()
    csv_fields = fields.Text()
    ### ends Fields
        
    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        if self.env.context.get('active_id'):
            report = self.env['ir.actions.report'].browse(self.env.context['active_ids'])
            if report.report_name == 'aeroo.printscreen.list':
                raise Warning(_("Print Screen report does not support this functionality!"))
        res = super(report_print_by_action, self).fields_view_get(view_id, 
            view_type, toolbar=toolbar, submenu=submenu)
        return res
    
    @api.model
    def _get_model(self):
        rep_obj = self.env['ir.actions.report']
        report = rep_obj.browse(self.env.context['active_ids'])
        return report[0].model
    
    @api.model
    def _get_last_ids(self):
        last_call = self.search([('name', '=', self._get_model()), ('create_uid', '=', self.env.uid)])
        return last_call and last_call[-1].object_ids or False

    @api.model
    def _get_csv(self):
        if not self.env.context.get('active_ids'):
            return None
        report = self.env['ir.actions.report'].browse(self.env.context['active_ids'])[0]
        
        i = 1
        l = []
        for k in self.env[report.model].search([])[0].read()[0].keys():
            l.append('%s. %s' % (i, k))
            i += 1
        #~ raise Warning(self.env[model]._fields.keys())
        csv = ', '.join(l)
        return csv

    _defaults = {
       'name': _get_model,
       'object_ids': _get_last_ids,
       'csv_fields': _get_csv,
    }

