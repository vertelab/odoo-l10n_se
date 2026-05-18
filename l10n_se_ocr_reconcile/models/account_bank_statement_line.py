import re
import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)

OCR_DIGIT_PATTERN = re.compile(r'(?<!\d)(\d{4,25})(?!\d)')


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    extracted_ocr = fields.Char(
        string='Extracted OCR',
        readonly=True,
        copy=False,
        index=True,
        help='OCR number extracted and validated from the bank transaction text.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Extract and validate OCR numbers when bank statement lines are created
        from Open Banking imports or manual entry."""
        for vals in vals_list:
            vals = self._extract_ocr_from_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        """Re-extract OCR if payment_ref or narration is updated."""
        vals = self._extract_ocr_from_vals(vals)
        return super().write(vals)

    def _extract_ocr_from_vals(self, vals):
        """Parse payment_ref or narration for candidate OCR strings,
        validate via Luhn check, and populate extracted_ocr.

        Returns the (possibly modified) vals dict.
        """
        if vals.get('extracted_ocr'):
            return vals

        text = vals.get('payment_ref') or vals.get('narration') or ''
        if not text:
            return vals

        ocr = self._find_valid_ocr(text)
        if ocr:
            vals['extracted_ocr'] = ocr
            _logger.debug(
                'Extracted OCR %s from statement line text: %s',
                ocr, text[:80],
            )
        return vals

    @api.model
    def _find_valid_ocr(self, text):
        """Search *text* for digit sequences of length 4-25 and return the
        first one that passes the Luhn (Modulo 10) check.

        Strips common Swedish bank prefixes / noise before scanning.
        """
        cleaned = self._clean_bank_text(text)
        for candidate in OCR_DIGIT_PATTERN.findall(cleaned):
            if self._luhn_validate(candidate):
                return candidate
        return None

    @api.model
    def _clean_bank_text(self, text):
        """Remove known noise patterns from Swedish Open Banking feeds.

        - Strips spaces embedded in digit groups (e.g. "1234 5678 9012")
        - Removes common prefixes like "REF", "KID", "OCR", "GIRO"
        - Removes common separators: dashes, dots, plus signs
        """
        text = text.upper()
        text = re.sub(r'\b(REF|KID|OCR|GIRO|REFERENS)\b[:\s]*', '', text)
        text = re.sub(r'[\s\-\.\+]+', '', text)
        return text

    @api.model
    def _luhn_validate(self, number_str):
        """Verify that *number_str* is a valid Luhn (Modulo 10) number.

        Uses the same weighting as l10n_se_ocr (2,1,2,1… right-to-left).
        Returns True when the check digit is correct.
        """
        if not number_str.isdigit():
            return False
        digits = [int(d) for d in number_str]
        digits.reverse()
        total = 0
        for i, d in enumerate(digits):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            total += d
        return total % 10 == 0
