import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.misc import formatLang, get_lang
from functools import partial

from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _amount_by_group(self):
        res = super(SaleOrder, self)._amount_by_group()
        for order in self:
            new_amount_by_group = []
            for line in order.amount_by_group:
                # ~ _logger.warning(f"{line[0]=}")
                tax_group = self.env['account.tax.group'].search([('name','=',line[0])])
                # ~ _logger.warning(f"{tax_group} {tax_group.name} {tax_group.hidden_tax}")
                if not tax_group.hidden_tax:
                   new_amount_by_group.append(line)
            # ~ _logger.warning(new_amount_by_group)
            order.amount_by_group = new_amount_by_group


    @api.depends('state', 'order_line.invoice_status')
    def _get_invoice_status(self):
        # ~ _logger.warning("_get_invoice_status"*100)
        res = super(SaleOrder, self)._get_invoice_status()
        for record in self:
            for line in record.order_line:
                line.max_sold_chem_tax = 0
                if record.invoice_status == "invoiced":
                    if line.product_id and line.product_id.hs_code_id and line.product_id.chemical_tax == line.product_id.hs_code_id.chemical_max_tax:
                        line.max_sold_chem_tax = line.product_uom_qty
        return res
        
        

                    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    hidden_tax = fields.Float(string="Hidden tax", readonly=True)
    subtotal_plus_hidden_tax = fields.Float(string="Subtotal plus hidden_tax", readonly=False, digits=(0,2))
    price_unit_plus_hidden_tax = fields.Float(string="Unit price plus hidden_tax", readonly=False, digits=(0,2))   

    chemical_tax = fields.Float(string="Chemical tax", help="Chemical tax for products in this category")
    
    max_sold_chem_tax = fields.Integer(
        string=_('Number Of sold products for the max chemical tax amount'),
        readonly=True,
    )
    
    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        super(SaleOrderLine,self)._compute_amount() 
        for line in self:
            line.hidden_tax = 0
            line.subtotal_plus_hidden_tax = line.price_subtotal
            line.price_unit_plus_hidden_tax = line.price_unit
            for tax in line.tax_id:
                if tax.hidden_tax == True:
                    if line.product_id.hs_code_id and line.order_id.partner_id:
                        hidden_tax = line.tax_id.filtered(lambda x: x.hidden_tax)
                        chem_tax = hidden_tax._compute_amount(line.price_subtotal,line.price_unit,line.product_uom_qty,line.product_id,line.order_id.partner_id)
                        line.price_subtotal += chem_tax
                        line.price_tax -= chem_tax                        
                        _logger.warning('%s'%line.tax_id.compute_all(line.price_subtotal, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id))     
                        if not tax.price_include:
                            line.subtotal_plus_hidden_tax += chem_tax
                            line.price_unit_plus_hidden_tax = line.subtotal_plus_hidden_tax/line.product_uom_qty   



