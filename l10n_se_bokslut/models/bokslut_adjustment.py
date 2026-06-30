# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class AccountBokslutAdjustment(models.Model):
    _name = 'account.bokslut.adjustment'
    _description = 'Closing Adjustment'
    _order = 'sequence'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Order', default=10)
    name = fields.Char(string='Description', required=True)
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        domain="[('company_id', '=', company_id)]",
    )
    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
    )
    type = fields.Selection(
        selection=[
            ('income', 'Taxable Income'),
            ('cost', 'Deductible Cost'),
            ('non_deductible', 'Non-Deductible Cost'),
            ('non_taxable', 'Non-Taxable Income'),
        ],
        string='Type',
        required=True,
        default='non_deductible',
    )
    is_permanent = fields.Boolean(
        string='Permanent Difference',
        help='A permanent difference only affects tax, not bookkeeping.',
        default=True,
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Verification',
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='bokslut_id.company_currency_id',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='bokslut_id.company_id',
    )
