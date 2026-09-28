# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<https://vertel.se>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountBokslutCurrencyRevaluation(models.Model):
    """Currency revaluation of open customer invoices / vendor bills.

    At year-end, open receivable (1510) and payable (2440) items in a
    foreign currency must be revalued at the closing rate. The difference
    between the booking rate and the closing rate is an unrealised
    exchange rate difference that must be posted (3960/7960) so that
    kundfordringar and leverantörsskulder show the correct amount in SEK.

    This model follows the same pattern as account.excess.depreciation:
    one line per open item, computed difference, and a generated move.
    """
    _name = 'account.bokslut.currency.revaluation'
    _description = 'Currency Revaluation of Open Items'
    _order = 'sequence, id'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Order', default=10)
    name = fields.Char(
        string='Description',
        compute='_compute_name',
        store=True,
        readonly=False,
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Partner',
        help='Customer (receivable) or vendor (payable) of the open item.',
    )
    account_id = fields.Many2one(
        comodel_name='account.account',
        string='Account',
        domain="[('company_id', '=', company_id)]",
        help='Receivable (1510) or payable (2440) account.',
    )
    move_line_id = fields.Many2one(
        comodel_name='account.move.line',
        string='Open Item',
        ondelete='set null',
        help='The open account.move.line being revalued.',
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Revaluation Entry',
        readonly=True,
        help='Generated revaluation verification.',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Item Currency',
        help='Currency of the open item (foreign currency).',
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='bokslut_id.company_currency_id',
        string='Company Currency',
    )
    amount_foreign = fields.Monetary(
        string='Amount in Currency',
        currency_field='currency_id',
        help='Open amount in the item currency.',
    )
    rate_booking = fields.Float(
        string='Booking Rate',
        digits=(12, 6),
        help='Exchange rate used when the item was booked.',
    )
    rate_closing = fields.Float(
        string='Closing Rate',
        digits=(12, 6),
        help='Exchange rate at the closing date.',
    )
    amount_company_booking = fields.Monetary(
        string='Booked (SEK)',
        currency_field='company_currency_id',
        help='Amount in company currency at the booking rate.',
    )
    amount_company_closing = fields.Monetary(
        string='Revalued (SEK)',
        currency_field='company_currency_id',
        compute='_compute_amount_company_closing',
        store=True,
        help='Amount in company currency at the closing rate.',
    )
    difference = fields.Monetary(
        string='Exchange Difference',
        currency_field='company_currency_id',
        compute='_compute_difference',
        store=True,
        help='Revalued - booked. Positive = gain for receivables, loss for payables.',
    )
    is_receivable = fields.Boolean(
        string='Receivable',
        compute='_compute_is_receivable',
        store=True,
        help='True for customer invoices (asset), False for vendor bills (liability).',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='bokslut_id.company_id',
    )

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends('partner_id', 'account_id', 'currency_id')
    def _compute_name(self):
        for rec in self:
            parts = []
            if rec.partner_id:
                parts.append(rec.partner_id.display_name)
            if rec.currency_id:
                parts.append(rec.currency_id.name)
            rec.name = ' — '.join(parts) if parts else _('Currency Revaluation')

    @api.depends('amount_foreign', 'rate_closing', 'company_currency_id')
    def _compute_amount_company_closing(self):
        for rec in self:
            rec.amount_company_closing = (rec.amount_foreign or 0.0) * (rec.rate_closing or 0.0)

    @api.depends('amount_company_closing', 'amount_company_booking')
    def _compute_difference(self):
        for rec in self:
            rec.difference = (rec.amount_company_closing or 0.0) - (rec.amount_company_booking or 0.0)

    @api.depends('account_id')
    def _compute_is_receivable(self):
        for rec in self:
            rec.is_receivable = rec.account_id.account_type == 'asset_receivable'

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    @api.model
    def _load_open_items_for(self, bokslut):
        """Load open foreign-currency items for a closing into revaluation lines.

        Reads account.move.line in the closing's company that are not
        reconciled and whose currency differs from the company currency.
        Fills one revaluation line per item with the booked residual and
        the closing rate. Previously loaded, not-yet-posted lines are
        replaced.
        """
        bokslut.ensure_one()
        if not bokslut.period_stop or not bokslut.period_stop.date_stop:
            raise UserError(_('The closing end period must be set before loading open items.'))

        closing_date = fields.Date.from_string(bokslut.period_stop.date_stop)
        company = bokslut.company_id
        company_currency = company.currency_id

        domain = [
            ('company_id', '=', company.id),
            ('parent_state', '=', 'posted'),
            ('reconciled', '=', False),
            ('currency_id', '!=', False),
            ('currency_id', '!=', company_currency.id),
            ('account_id.account_type', 'in', ('asset_receivable', 'liability_payable')),
            ('date', '<=', closing_date),
        ]

        lines = self.env['account.move.line'].search(domain)

        # Remove previously loaded, not-yet-posted lines for this closing
        bokslut.currency_revaluation_ids.filtered(lambda r: not r.move_id).unlink()

        for line in lines:
            rate_closing = line.currency_id._get_conversion_rate(
                line.currency_id, company_currency, company, closing_date)
            # Booking rate = the rate at the item's own date (same source as Odoo
            # uses when the item was booked), avoids fragile balance/amount_currency.
            rate_booking = line.currency_id._get_conversion_rate(
                line.currency_id, company_currency, company, line.date)
            self.create({
                'bokslut_id': bokslut.id,
                'partner_id': line.partner_id.id,
                'account_id': line.account_id.id,
                'move_line_id': line.id,
                'currency_id': line.currency_id.id,
                'amount_foreign': line.amount_residual_currency,
                'rate_booking': rate_booking,
                'rate_closing': rate_closing,
                'amount_company_booking': line.amount_residual,
            })
        return True

    def _get_difference_account(self):
        """Return the exchange-difference account (3960/7960) for this line."""
        self.ensure_one()
        company = self.bokslut_id.company_id
        code = '3960' if self.is_receivable else '7960'
        account = self.env['account.account'].search([
            ('code', '=', code),
            ('company_id', '=', company.id),
        ], limit=1)
        if not account:
            # Fall back to the company's configured exchange gain/loss accounts
            account = company.income_currency_exchange_account_id if self.is_receivable \
                else company.expense_currency_exchange_account_id
        if not account:
            raise UserError(_('No exchange difference account (%s) found.') % code)
        return account

    def _get_revaluation_journal(self):
        self.ensure_one()
        company = self.bokslut_id.company_id
        journal = self.env['account.journal'].search([
            ('code', '=', 'Ovr'),
            ('company_id', '=', company.id),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', company.id),
            ], limit=1)
        if not journal:
            raise UserError(_('No general journal found.'))
        return journal

    def action_create_move(self):
        """Create one revaluation verification for all lines in this recordset.

        The verification posts the exchange difference on the receivable/
        payable account against the exchange difference account, so the
        balance-sheet amount reflects the closing rate. All lines must
        belong to the same closing.
        """
        lines = self.filtered(lambda r: r.difference and not r.move_id)
        if not lines:
            raise UserError(_('No revaluation lines with a difference to post.'))
        bokslut = lines.mapped('bokslut_id')
        if len(bokslut) != 1:
            raise UserError(_('All revaluation lines must belong to the same closing.'))
        bokslut.ensure_one()
        if not bokslut.period_stop or not bokslut.period_stop.date_stop:
            raise UserError(_('The closing end period must be set.'))

        closing_date = fields.Date.from_string(bokslut.period_stop.date_stop)
        journal = lines[0]._get_revaluation_journal()

        entry = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': closing_date,
            'ref': _('Valutavärdering %s') % bokslut.fiscalyear_id.name,
            'move_type': 'entry',
        })

        move_lines = []
        for rec in lines:
            diff = rec.difference
            # Receivable: increase (debit) on gain, decrease (credit) on loss.
            # Payable: opposite sign.
            sign = 1.0 if rec.is_receivable else -1.0
            amount = abs(diff)
            if diff >= 0:
                debit, credit = (amount, 0.0) if sign > 0 else (0.0, amount)
            else:
                debit, credit = (0.0, amount) if sign > 0 else (amount, 0.0)

            move_lines.append((0, 0, {
                'name': rec.name,
                'account_id': rec.account_id.id,
                'partner_id': rec.partner_id.id,
                'currency_id': rec.currency_id.id,
                'debit': debit,
                'credit': credit,
            }))
            # Offsetting exchange difference line (opposite)
            diff_account = rec._get_difference_account()
            move_lines.append((0, 0, {
                'name': rec.name,
                'account_id': diff_account.id,
                'partner_id': rec.partner_id.id,
                'debit': credit,
                'credit': debit,
            }))

        entry.write({'line_ids': move_lines})
        lines.write({'move_id': entry.id})
        return {
            'type': 'ir.actions.act_window',
            'name': _('Revaluation Entry'),
            'res_model': 'account.move',
            'res_id': entry.id,
            'view_mode': 'form',
        }

    def action_open_partner_statement(self):
        """Open the partner_statement report for the selected partner.

        Reuses the partner_statement module (T/11336) so the accountant can
        see the underlying open items behind the revaluation line.
        """
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('No partner set on this line.'))
        report = self.env.ref('partner_statement.outstanding_statement_wizard_action', raise_if_not_found=False)
        if not report:
            raise UserError(_('partner_statement is not installed.'))
        action = report.read()[0]
        action['context'] = {'active_ids': self.partner_id.ids}
        return action
