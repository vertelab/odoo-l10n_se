import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
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


    @api.depends('price_unit', 'categ_id.chemical_tax')
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
        _logger.warn("fields=%s groupby = %s" % (fields, groupby))
        return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)
