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

class account_tax_esdk(models.Model):
    """
      
      https://support.speedledger.se/hc/sv/articles/204207739-Momskoder
      
      
    """

    _name = 'account.tax.esdk'
    _description = 'Tax reporting'
    _order = 'name'

    name = fields.Char('Tax Period',required=True,help="Skattemyndighetens tax period. Usually YYYYMM")
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
    description = fields.Text('Note', help="This will be included in the message")

 

    @api.model
    def get_tax_sum(self,code):
        account_tax = self.env['account.tax'].search([('description','=',code)])
        if not account_tax or len(account_tax) == 0:
            return _("Error in code %s" % code)
        #_logger.warning("This is tax  %s / %s" % (self.env['account.tax.code'].browse(account_tax.tax_code_id.id).name,code))
        return self.env['account.tax.code'].with_context(
                    {'period_ids': [p.id for p in self.env['account.period'].search([('date_start', '>=', self.period_start.date_start), ('date_stop', '<=', self.period_end.date_stop)])],  # Special periods?
                     'state': 'all'}
                ).browse(account_tax.tax_code_id.id).sum_periods or 0

    @api.one
    def create_tax_sum_attachement(self,):
        self.env['ir.attachment'].create({
            'name':  'Moms%s.xml' % self.name,
            'datas_fname': 'Moms%s.xml' % self.name,
            'res_model': self._name,
            'res_id': self.id,
            'datas':  base64.b64encode(self.pool.get('ir.ui.view').render(self._cr,self._uid,'l10n_se_esdk.esdk_period_moms',values={'doc': self})),
        })

    @api.one
    def create_ag_sum_attachement(self,):
        self.env['ir.attachment'].create({
            'name':  'Ag%s.xml' % self.name,
            'datas_fname': 'Ag%s.xml' % self.name,
            'res_model': self._name,
            'res_id': self.id,
            'datas':  base64.b64encode(self.pool.get('ir.ui.view').render(self._cr,self._uid,'l10n_se_esdk.esdk_period_ag',values={'doc': self})),
        })

#----------------------------------------------------------
# Tax
#----------------------------------------------------------

class account_tax_code(models.Model):
    _inherit = 'account.tax.code'

    @api.one
    def _sum_periods(self):
        #~ context = { 'period_ids': self.env['account.period'].search([('date_start', '>=', self.period_start.date_start), ('date_stop', '<=', self.period_end.date_stop)]),
                    #~ 'state': 'all'}
        move_state = ('draft', 'posted', )
        period_ids = "(" + ','.join([str(p) for p in self._context['period_ids']]) + ")"
        amount = self.pool.get('account.tax.code')._sum(self._cr,self._uid,[self.id],'',[],context=self._context,
        where=' AND line.period_id IN %s AND move.state IN %s' % (period_ids,move_state), where_params=()) or 0.0
        _logger.warning("This is tax  %s " % (','.join([str(p) for p in self._context['period_ids']])))
        self.sum_periods = amount[self.id]
    sum_periods = fields.Float('Periods Sum',compute='_sum_periods')
    
    

