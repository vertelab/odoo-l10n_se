import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)


class SaleReport(models.Model):
    _inherit = "sale.report"
    
    chemical_tax = fields.Float(
        string=_('Chemical tax'),
        readonly=True
    )

    net_weight = fields.Float('Netto Vikt', readonly=True)
    max_chem_tax = fields.Integer('Antal sålda produkter med max kemskatt', readonly=True)

    product_id = fields.Many2one(
        comodel_name="product.product",
        readonly=True,
    )
    # def _select_sale(self, fields=None):
    #     _logger.warning("_select_sale"*100)
    #     res = super(SaleReport, self)._select_sale(fields)
    #     res_list = res.split(",")
    #     for line in res_list:
    #         _logger.warning(f"{line=}")
    #     #Add chemical tax to the pivot view
    #     res = res + ",l.product_uom_qty * p.chemical_tax as chemical_tax"
    #     _logger.warning(f"{res=}")
    #     return res


    def _select_sale(self, fields=None):
        if not fields:
            fields = {}
        select_ = """
            coalesce(min(l.id), -s.id) as id,
            l.product_id as product_id,
            t.uom_id as product_uom,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as product_uom_qty,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_delivered / u.factor * u2.factor) ELSE 0 END as qty_delivered,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_invoiced / u.factor * u2.factor) ELSE 0 END as qty_invoiced,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.qty_to_invoice / u.factor * u2.factor) ELSE 0 END as qty_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.price_total / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as price_total,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.price_subtotal / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as price_subtotal,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.untaxed_amount_to_invoice / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount_to_invoice,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.untaxed_amount_invoiced / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) ELSE 0 END as untaxed_amount_invoiced,
            count(*) as nbr,
            s.name as name,
            s.date_order as date,
            s.state as state,
            s.partner_id as partner_id,
            s.user_id as user_id,
            s.company_id as company_id,
            s.campaign_id as campaign_id,
            s.medium_id as medium_id,
            s.source_id as source_id,
            extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
            t.categ_id as categ_id,
            s.pricelist_id as pricelist_id,
            s.analytic_account_id as analytic_account_id,
            s.team_id as team_id,
            p.product_tmpl_id,
            partner.country_id as country_id,
            partner.industry_id as industry_id,
            partner.commercial_partner_id as commercial_partner_id,
            CASE WHEN l.product_id IS NOT NULL THEN sum(p.weight * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as weight,
            CASE WHEN l.product_id IS NOT NULL THEN sum(p.volume * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as volume,
            l.discount as discount,
            CASE WHEN l.product_id IS NOT NULL THEN sum((l.price_unit * l.product_uom_qty * l.discount / 100.0 / CASE COALESCE(s.currency_rate, 0) WHEN 0 THEN 1.0 ELSE s.currency_rate END))ELSE 0 END as discount_amount,
            s.id as order_id,
            CASE WHEN l.product_id IS NOT NULL THEN sum(p.chemical_tax * l.product_uom_qty) ELSE 0 END as chemical_tax,
            CASE WHEN l.product_id IS NOT NULL THEN sum(p.net_weight * l.product_uom_qty / u.factor * u2.factor) ELSE 0 END as net_weight,
            CASE WHEN l.product_id IS NOT NULL THEN sum(l.max_sold_chem_tax) ELSE 0 END as max_chem_tax
        """

        for field in fields.values():
            select_ += field
        return select_

    # def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
    #       fields['chemical_tax'] = ", p.chemical_tax * l.product_uom_qty as chemical_tax"
    #       groupby += ', p.chemical_tax'
    #       _logger.warn("fields=%s groupby = %s" % (fields, groupby))
    #       return super(SaleReport, self)._query(with_clause, fields, groupby, from_clause)


