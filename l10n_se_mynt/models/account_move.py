from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import json
from datetime import datetime, date, timedelta


class AccountMove(models.Model):
    _inherit = 'account.move'

    invoice_outstanding_mynt_credits_debits_widget = fields.Text(
        groups="account.group_account_invoice,account.group_account_readonly",
        compute='_compute_payments_widget_to_reconcile_mynt', store=True)

    @api.depends('state', 'amount_total')
    def _compute_payments_widget_to_reconcile_mynt(self):
        for move in self:
            move.invoice_outstanding_credits_debits_widget = json.dumps(False)
            move.invoice_outstanding_mynt_credits_debits_widget = json.dumps(False)
            move.invoice_has_outstanding = False

            if move.state != 'posted' \
                    or move.payment_state not in ('not_paid', 'partial') \
                    or not move.is_invoice(include_receipts=True):
                continue

            pay_term_lines = move.line_ids\
                .filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))

            domain = [
                ('journal_id.name', '=', 'Mynt'),
                ('account_id', 'in', pay_term_lines.account_id.ids),
                ('parent_state', '=', 'posted'),
                ('reconciled', '=', False),
                '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0),
            ]

            payments_widget_vals = {'outstanding': True, 'content': [], 'move_id': move.id}

            if move.is_inbound():
                domain.append(('balance', '<', 0.0))
                payments_widget_vals['title'] = _('Outstanding credits')
            else:
                domain.append(('balance', '>', 0.0))
                payments_widget_vals['title'] = _('Outstanding debits')

            for line in self.env['account.move.line'].search(domain):

                if line.currency_id == move.currency_id:
                    # Same foreign currency.
                    amount = abs(line.amount_residual_currency)
                else:
                    # Different foreign currencies.
                    amount = move.company_currency_id._convert(
                        abs(line.amount_residual),
                        move.currency_id,
                        move.company_id,
                        line.date,
                    )

                if move.currency_id.is_zero(amount):
                    continue

                payments_widget_vals['content'].append({
                    'journal_name': line.ref or line.move_id.name,
                    'amount': amount,
                    'currency': move.currency_id.symbol,
                    'id': line.id,
                    'move_id': line.move_id.id,
                    'position': move.currency_id.position,
                    'digits': [69, move.currency_id.decimal_places],
                    'payment_date': fields.Date.to_string(line.date),
                })

            if not payments_widget_vals['content']:
                continue

            move.invoice_outstanding_credits_debits_widget = json.dumps(payments_widget_vals)
            move.invoice_outstanding_mynt_credits_debits_widget = json.dumps(payments_widget_vals)
            move.invoice_has_outstanding = True

    def reconcile_mynt_accounts_wizard(self):
        view_id = self.env.ref('l10n_se_mynt.mynt_reconcile_wizard').id
        return {
            'name': _('Reconcile your bills'),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'view_mode': 'form',
            'res_model': 'mynt.account.move.reconcile.wizard',
            'views': [[view_id, 'form']],
        }


class AccountMoveMyntWizard(models.TransientModel):
    _name = 'mynt.account.move.reconcile.wizard'

    def _set_default_card_mynt_transaction(self):
        start_of_current_month = date.today().replace(day=1)
        start_of_previous_month = (start_of_current_month - timedelta(days=1)).replace(day=1)
        account_card_statement_id = self.env['account.card.statement'].search([('date', '=', start_of_previous_month)])
        return account_card_statement_id.id or False

    account_card_transaction_id = fields.Many2one('account.card.statement', string="Account Card Transactions",
                                                  required=True, default=_set_default_card_mynt_transaction)
    move_id = fields.Many2one('account.move', string="Account Move", required=True,
                              default=lambda self: self.env.context.get('active_id', None))

    def reconcile_mynt_accounts(self):
        if self.move_id and self.account_card_transaction_id:
            account_statement_line_ids = self.account_card_transaction_id.account_card_statement_line_ids.filtered(
                lambda line: line.description != 'Credit Repayment' and line.amount < 0
            )

            move_ids = account_statement_line_ids.mapped('account_move_id').filtered(
                lambda move_id: (move_id.state == 'posted') and (move_id.payment_state != 'paid'))
            if not move_ids:
                raise ValidationError(_("No items to reconcile"))
            credit_lines = move_ids.line_ids.filtered(lambda line_id: line_id.credit > 0)
            self.move_id.js_assign_outstanding_line(credit_lines.ids)
