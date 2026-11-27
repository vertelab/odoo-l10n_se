import re
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    ocr_number = fields.Char(
        string='OCR Number',
        compute='_compute_ocr_number',
        store=True,
        readonly=True,
        copy=False,
        index=True,
    )

    @api.depends('name', 'move_type')
    def _compute_ocr_number(self):
        """Generates OCR number for customer invoices based on the active
        configuration setting (soft or hard_fixed)."""
        control_level = self.env['ir.config_parameter'].sudo().get_param(
            'l10n_se_ocr.ocr_control_level', 'soft'
        )
        fixed_length = int(self.env['ir.config_parameter'].sudo().get_param(
            'l10n_se_ocr.ocr_fixed_length', 9
        ))

        for move in self:
            if move.move_type == 'out_invoice' and move.name and move.name != '/':
                digits_only = re.sub(r'\D', '', move.name)
                if digits_only:
                    if control_level == 'hard_fixed':
                        move.ocr_number = move._generate_hard_fixed_ocr(digits_only, fixed_length)
                    else:
                        move.ocr_number = move._generate_soft_ocr(digits_only)
                else:
                    move.ocr_number = False
            else:
                move.ocr_number = False

    def _generate_soft_ocr(self, digits):
        """Soft control: Append Luhn check digit to the cleaned invoice number."""
        check_digit = self._luhn_check(digits)
        return f"{digits}{check_digit}"

    def _generate_hard_fixed_ocr(self, digits, total_length):
        """Hard Fixed control:
        1. Pad with leading zeros (or truncate) to fit total_length - 1 (last digit is Luhn).
        2. The second-to-last digit represents total_length % 10.
        3. Append Luhn check digit as the final digit."""
        length_digit = total_length % 10
        base_length = total_length - 2

        if len(digits) > base_length:
            digits = digits[-base_length:]
        else:
            digits = digits.zfill(base_length)

        ocr_base = f"{digits}{length_digit}"
        check_digit = self._luhn_check(ocr_base)
        return f"{ocr_base}{check_digit}"

    @api.model
    def _luhn_check(self, number_str):
        """Calculate Luhn (Modulo 10) check digit.
        Standard Swedish KID-nummer weighting: 2,1,2,1... from right to left."""
        digits = [int(d) for d in number_str]
        digits.reverse()
        total = 0
        for i, d in enumerate(digits):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        return (10 - (total % 10)) % 10

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, order=None):
        """Extends search to match OCR numbers alongside standard fields
        in Kanban, List, Many2one, and Reconciliation views."""
        args = list(args or [])
        if name:
            ocr_domain = [('ocr_number', operator, name)]
            ocr_ids = self.search(ocr_domain + args, limit=limit).ids
            if ocr_ids:
                return ocr_ids
        return super()._name_search(name, args, operator, limit, order)
