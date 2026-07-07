# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class AccountDeclaration(models.Model):
    _inherit = 'account.declaration'

    payment_ids_count = fields.Integer(
        compute='_compute_payment_ids_count',
        string='Payment Orders',
    )

    def _compute_payment_ids_count(self):
        for rec in self:
            rec.payment_ids_count = len(rec._get_payment_orders())

    def _get_payment_orders(self):
        self.ensure_one()
        payment_order = []
        if self.move_id:
            for line in self.move_id.line_ids:
                pay_line = self.env['account.payment.line'].search([
                    ('move_line_id', '=', line.id),
                ], limit=1)
                if pay_line:
                    payment_order.append(pay_line.order_id.id)
        return payment_order

    def show_payment_orders(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account_payment_order.account_payment_order_outbound_action')
        action.update({
            'display_name': _('%s') % self.name,
            'domain': [('id', 'in', self._get_payment_orders())],
        })
        return action
