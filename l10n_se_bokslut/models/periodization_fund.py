# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountPeriodizationFund(models.Model):
    _name = 'account.periodization.fund'
    _description = 'Periodization Fund'
    _order = 'year desc'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='cascade',
    )
    year = fields.Integer(
        string='Allocation Year',
        required=True,
        default=lambda self: fields.Date.today().year - 1,
    )
    amount = fields.Monetary(
        string='Allocated Amount',
        currency_field='currency_id',
        required=True,
    )
    remaining = fields.Monetary(
        string='Remaining',
        currency_field='currency_id',
        compute='_compute_remaining',
        store=True,
    )
    reversal_amount = fields.Monetary(
        string='Reversal This Year',
        currency_field='currency_id',
        default=0.0,
    )
    reversal_year = fields.Integer(
        string='Last Reversal Year',
        help='Year by which this fund must be reversed (allocation year + 6).',
    )
    state = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('partially_reversed', 'Partially Reversed'),
            ('fully_reversed', 'Fully Reversed'),
        ],
        string='State',
        compute='_compute_state',
        store=True,
    )
    is_mandatory_reversal = fields.Boolean(
        string='Mandatory Reversal',
        compute='_compute_is_mandatory_reversal',
        store=True,
        help='True if this fund must be reversed this year (year + 6 rule).',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='bokslut_id.company_currency_id',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='bokslut_id.company_id',
    )

    @api.depends('amount', 'reversal_amount')
    def _compute_remaining(self):
        for rec in self:
            total_reversed = rec.reversal_amount or 0.0
            # Also sum reversals from other bokslut (if any)
            rec.remaining = max(0.0, rec.amount - total_reversed)

    @api.depends('remaining', 'amount')
    def _compute_state(self):
        for rec in self:
            if rec.remaining <= 0:
                rec.state = 'fully_reversed'
            elif rec.remaining < rec.amount:
                rec.state = 'partially_reversed'
            else:
                rec.state = 'active'

    @api.depends('year', 'bokslut_id.period_stop')
    def _compute_is_mandatory_reversal(self):
        for rec in self:
            if rec.bokslut_id.period_stop and rec.bokslut_id.period_stop.date_stop:
                year_end = fields.Date.from_string(rec.bokslut_id.period_stop.date_stop).year
                # Mandatory reversal if year_end >= allocation_year + 6
                rec.is_mandatory_reversal = year_end >= rec.year + 6
            else:
                rec.is_mandatory_reversal = False

    def action_reverse(self, amount):
        """Reverse (part of) a periodization fund."""
        self.ensure_one()
        if amount > self.remaining:
            raise UserError(_('Cannot reverse more than the remaining amount.'))
        self.reversal_amount = (self.reversal_amount or 0.0) + amount
        # Clear remaining (will be recomputed)
        self.remaining = max(0.0, self.amount - self.reversal_amount)

    @api.model
    def calculate_schablonintakt(self, bokslut):
        """Calculate schablonintäkt on periodization funds.
        
        Schablonintäkt = statslåneränta × summa periodiseringsfonder at beginning of year.
        For 2025 tax year, statslåneräntan is 2.5%.
        """
        if not bokslut.period_start or not bokslut.period_start.date_start:
            return 0.0
        year_start = fields.Date.from_string(bokslut.period_start.date_start).year

        # Find all active periodization funds at beginning of fiscal year
        all_funds = self.search([
            ('company_id', '=', bokslut.company_id.id),
            ('year', '<', year_start),
            ('state', '!=', 'fully_reversed'),
        ])
        total = sum(f.remaining for f in all_funds)

        # Statslåneränta — use company config or default 2.5%
        rate = bokslut.company_id.bokslut_schablon_ranta or 2.5
        return total * (rate / 100.0)
