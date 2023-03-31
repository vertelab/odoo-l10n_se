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
                _logger.warning(f"{line[0]=}")
                tax_group = self.env['account.tax.group'].search([('name','=',line[0])])
                _logger.warning(f"{tax_group} {tax_group.name} {tax_group.hidden_tax}")
                if not tax_group.hidden_tax:
                   new_amount_by_group.append(line)
            _logger.warning(new_amount_by_group)
            order.amount_by_group = new_amount_by_group



    @api.depends('order_line.price_total','order_line.tax_id','order_line.tax_id.hidden_tax')
    def _amount_all(self):
        res = super(SaleOrder,self)._amount_all()
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            for line in order.order_line:
                chem_tax = 0
                if line.tax_id.filtered(lambda x: x.hidden_tax) and line.product_id.hs_code_id and order.partner_id:
                   hidden_tax = line.tax_id.filtered(lambda x: x.hidden_tax)
                   chem_tax = hidden_tax._compute_amount(line.price_subtotal,line.price_unit,line.product_uom_qty,line.product_id,order.partner_id)
                   order.amount_untaxed += chem_tax
                   order.amount_tax -= chem_tax
        return res
        

    
            
       
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    _inherit = "product.category"    

    chemical_tax = fields.Float(
        string=_('Chemical tax'),
        readonly=True
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    price_with_chemtax = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )

    @api.depends('price_unit', 'product_id.categ_id.chemical_tax')
    def _get_price_reduce(self):
        for line in self:
            line.price_reduce = line.price_unit * (1.0 - line.discount / 100.0)


class SaleReport(models.Model):
    _inherit = "sale.report"
    
    chemical_tax = fields.Float(
        string=_('Chemical tax'),
        readonly=True
    )

    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['chemical_tax'] = ", p.chemical_tax as chemical_tax"
        groupby += ', p.chemical_tax'
        _logger.warning("fields=%s groupby = %s" % (fields, groupby))
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
