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
from openerp import models, fields, api, _
import re

import logging
_logger = logging.getLogger(__name__)


class account_invoice_serial(models.Model):
    _name = 'account.invoice.serial'
    _description = "Product serial numbers"
    _order = 'name'

    @api.one
    def _partner(self):
        self.partner_id = self.line_id.invoice_id.partner_id

    #~ def _serial_number(self):
        #~ _logger.warning('Self %r %s' % (self.line_id.product_id,self.product_id))
        #~ if self.product_id:
#~            return self.product_id.serial_type._next()
            
    name = fields.Char('Serial Number',track_visibility='always')
    line_id = fields.Many2one('account.invoice.line',)
    invoice_id = fields.Many2one('account.invoice',)
    product_id = fields.Many2one('product.product', string='Product',)
    partner_id = fields.Many2one('res.partner',compute='_partner',store=True)

    
    
    
class account_invoice(models.Model):
    _inherit = 'account.invoice'
   
    @api.multi
    def assign_serial_numbers(self):
        for invoice in self:
            for line in invoice.invoice_line:
                if not line.id in [l.id for l in invoice.serial_number_ids]:
                    for i in range(0,int(line.quantity)):
                        for serial_type in line.product_id.serial_type_ids:
                            serial = self.env['account.invoice.serial'].create({'line_id': line.id, 'invoice_id': line.invoice_id.id, 'product_id': line.product_id.id})
                            serial.name = serial_type._next()

    serial_number_ids = fields.One2many(comodel_name='account.invoice.serial', inverse_name='invoice_id', string='Serial numbers', track_visibility="always",readonly=True, copy=False)


class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'
   
#    serial_number = fields.Char('Serial Number',track_visibility='onchange')
    serial_number_ids = fields.One2many(comodel_name='account.invoice.serial', inverse_name='line_id', string='Serial numbers', readonly=False, copy=False)
    @api.one
    def _serial_numbers(self):
        if self.serial_number_ids and len(self.serial_number_ids)>0:
            self.serial_numbers = ', '.join([s.name for s in self.serial_number_ids])
    serial_numbers = fields.Char('Serial Numbers',compute="_serial_numbers",readonly=True)


class ir_sequence(models.Model):
    _inherit="ir.sequence"
    
    product_id = fields.Many2one(comodel_name="product.product",string="Product")


class product_product(models.Model):
    _inherit = "product.product"

    serial_type_ids = fields.One2many(comodel_name='ir.sequence',inverse_name="product_id",string="Serial number",help="Sequence from new serial numbers are taken")
    serial_number_ids = fields.One2many(comodel_name='account.invoice.serial', inverse_name='product_id', string='Serial numbers', readonly=True, copy=False)

class res_partner(models.Model):
    _inherit = "res.partner"

    serial_number_ids = fields.One2many(comodel_name='account.invoice.serial', inverse_name='partner_id', string='Serial numbers', readonly=True, copy=False)
    @api.one
    def _num_serial_number(self):
        return len(self.serial_number_ids)
    num_serial_numbers = fields.Integer(compute=_num_serial_number) 

    
