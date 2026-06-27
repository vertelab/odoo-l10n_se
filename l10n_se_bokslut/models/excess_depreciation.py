# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountExcessDepreciation(models.Model):
    _name = 'account.excess.depreciation'
    _description = 'Excess Depreciation'
    _order = 'sequence'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Order', default=10)
    name = fields.Char(string='Description', required=True)
    asset_id = fields.Many2one(
        comodel_name='account.asset',
        string='Asset',
        help='Link to the asset register for automatic value retrieval.',
    )
    asset_category = fields.Selection(
        selection=[
            ('intangible', 'Intangible Assets'),
            ('buildings', 'Buildings and Land'),
            ('machinery', 'Machinery and Equipment'),
            ('inventory', 'Inventory, Tools, Installations'),
        ],
        string='Asset Category',
        required=True,
    )
    book_value_ib = fields.Monetary(
        string='Book Value (Opening)',
        currency_field='currency_id',
        default=0.0,
    )
    acquisitions = fields.Monetary(
        string='Acquisitions',
        currency_field='currency_id',
        default=0.0,
    )
    disposals = fields.Monetary(
        string='Disposals',
        currency_field='currency_id',
        default=0.0,
    )
    book_depreciation = fields.Monetary(
        string='Book Depreciation',
        currency_field='currency_id',
        default=0.0,
        help='Depreciation according to plan (planenlig avskrivning).',
    )
    book_value_ub = fields.Monetary(
        string='Book Value (Closing)',
        currency_field='currency_id',
        compute='_compute_book_value',
        store=True,
    )
    tax_rest_value_ib = fields.Monetary(
        string='Tax Rest Value (Opening)',
        currency_field='currency_id',
        default=0.0,
        help='Skattemässigt restvärde vid årets början.',
    )
    tax_rest_value_base = fields.Monetary(
        string='Tax Base for Depreciation',
        currency_field='currency_id',
        compute='_compute_tax_base',
        store=True,
        help='IB + acquisitions - disposals.',
    )
    tax_min_value = fields.Monetary(
        string='Min Tax Value',
        currency_field='currency_id',
        compute='_compute_tax_min_value',
        store=True,
        help='Lowest allowed tax value (70% of base for huvudregeln, 80% for kompletteringsregeln).',
    )
    tax_depreciation = fields.Monetary(
        string='Tax Depreciation',
        currency_field='currency_id',
        compute='_compute_tax_depreciation',
        store=True,
        help='Maximum tax depreciation allowed.',
    )
    planned_depreciation = fields.Monetary(
        string='Planned Excess Depreciation',
        currency_field='currency_id',
        default=0.0,
        help='How much excess depreciation to apply this year.',
    )
    excess_depreciation = fields.Monetary(
        string='Excess Depreciation',
        currency_field='currency_id',
        compute='_compute_excess',
        store=True,
        help='Difference between book and tax depreciation for this year.',
    )
    rule = fields.Selection(
        selection=[
            ('main', 'Huvudregel (30%)'),
            ('complement', 'Kompletteringsregel (20%)'),
        ],
        string='Rule',
        required=True,
        default='main',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='bokslut_id.company_currency_id',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='bokslut_id.company_id',
    )

    @api.onchange('asset_id')
    def _onchange_asset_id(self):
        """Auto-fill values from the linked asset."""
        if self.asset_id:
            if not self.name:
                self.name = self.asset_id.name

    @api.depends('book_value_ib', 'acquisitions', 'disposals', 'book_depreciation')
    def _compute_book_value(self):
        for rec in self:
            rec.book_value_ub = (rec.book_value_ib or 0.0) + (rec.acquisitions or 0.0) - (rec.disposals or 0.0) - (rec.book_depreciation or 0.0)

    @api.depends('tax_rest_value_ib', 'acquisitions', 'disposals')
    def _compute_tax_base(self):
        for rec in self:
            rec.tax_rest_value_base = (rec.tax_rest_value_ib or 0.0) + (rec.acquisitions or 0.0) - (rec.disposals or 0.0)

    @api.depends('tax_rest_value_base', 'rule')
    def _compute_tax_min_value(self):
        for rec in self:
            if rec.rule == 'main':
                # Huvudregeln: min 70% av basen
                rec.tax_min_value = (rec.tax_rest_value_base or 0.0) * 0.70
            else:
                # Kompletteringsregeln: min 80% av basen
                rec.tax_min_value = (rec.tax_rest_value_base or 0.0) * 0.80

    @api.depends('tax_rest_value_base', 'tax_min_value')
    def _compute_tax_depreciation(self):
        for rec in self:
            # Max tax depreciation = tax_base - min_tax_value
            rec.tax_depreciation = max(0.0, (rec.tax_rest_value_base or 0.0) - (rec.tax_min_value or 0.0))

    @api.depends('planned_depreciation', 'book_depreciation')
    def _compute_excess(self):
        for rec in self:
            rec.excess_depreciation = max(0.0, (rec.planned_depreciation or 0.0) - (rec.book_depreciation or 0.0))
