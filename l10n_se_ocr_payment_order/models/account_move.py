from odoo import api, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_payment_order_communication_direct(self):
        """Inject OCR number as the payment communication when available.
        This ensures the OCR number flows into payment lines and SEPA exports."""
        self.ensure_one()
        if self.move_type == 'out_invoice' and self.ocr_number:
            return self.ocr_number
        return super()._get_payment_order_communication_direct()

    @api.model_create_multi
    def create(self, vals_list):
        """Set reference_type to 'structured' for customer invoices with OCR number."""
        moves = super().create(vals_list)
        for move in moves:
            if move.move_type == 'out_invoice' and move.ocr_number:
                move.sudo().reference_type = 'structured'
        return moves

    def write(self, vals):
        """Set reference_type to 'structured' when OCR number becomes available."""
        result = super().write(vals)
        for move in self:
            if move.move_type == 'out_invoice' and move.ocr_number:
                move.sudo().reference_type = 'structured'
        return result
