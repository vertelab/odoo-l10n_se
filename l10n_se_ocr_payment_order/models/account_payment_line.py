from odoo import api, fields, models


class AccountPaymentLine(models.Model):
    _inherit = 'account.payment.line'

    ocr_number = fields.Char(
        string='OCR Number',
        compute='_compute_ocr_number',
        store=True,
        readonly=True,
    )

    @api.depends('move_line_id', 'move_line_id.move_id.ocr_number')
    def _compute_ocr_number(self):
        for line in self:
            line.ocr_number = line.move_line_id.move_id.ocr_number or False
