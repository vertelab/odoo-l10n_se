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
import re

import logging
_logger = logging.getLogger(__name__)


class account_invoice_line_serial(models.Model):
    _name = 'account.invoice.line.serial'
    _description = "Product serial numbers"
    _order = 'name'

    @api.one
    def _partner(self):
        self.partner_id = self.line_id.invoice_id.partner_id

    def _serial_number(self):
        if self.product_id:
            return self.product_id.serial_type._next()

    name = fields.Char('Serial Number',default=_serial_number)
    line_id = fields.Many2one('account.invoice.line',)
    invoice_id = fields.Many2one('account.invoice',)
    product_id = fields.Many2one('product.product', string='Product')
    partner_id = fields.Many2one('res.partner',compute='_partner')

class account_invoice(models.Model):
    _inherit = 'account.invoice'
   
    #~ @api.multi
    #~ def action_move_create(self):
        #~ if super(account_invoice,self).action_move_create():
            #~ for line in self.invoice_line:
                #~ _logger.warning('Action_move  %s %s %s' % (line.product_id,line.product_id.serial_type,line.serial_number))
                #~ if line.product_id and line.product_id.serial_type and line.serial_number == False:
                    #~ line.neserial_number = line.product_id.serial_type._next()
                    
    @api.multi
    def assign_serial_numbers(self):
        for invoice in self:
            for line in invoice.invoice_line:
                if not line.id in [l.id for l in invoice.serial_number_ids]:
                    for i in range(0,int(line.quantity)):
                        self.env['account.invoice.line.serial'].create({'product_id': line.product_id.id, 'line_id': line.id, 'invoice_id': line.invoice_id.id})

    serial_number_ids = fields.One2many(comodel_name='account.invoice.line.serial', inverse_name='invoice_id', string='Serial numbers', readonly=True, copy=False)


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
   
#    serial_number = fields.Char('Serial Number',track_visibility='onchange')
    serial_number_ids = fields.One2many(comodel_name='account.invoice.line.serial', inverse_name='line_id', string='Serial numbers', readonly=True, copy=False)



    

class product_product(models.Model):
    _inherit = "product.product"

    serial_type = fields.Many2one('ir.sequence',string="Serial number",help="Sequence from new serial numbers are taken")
    serial_number_ids = fields.One2many(comodel_name='account.invoice.line.serial', inverse_name='product_id', string='Serial numbers', readonly=True, copy=False)
        
