from odoo import api, fields, models,_
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)

class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.constrains('invoice_repartition_line_ids', 'refund_repartition_line_ids', 'repartition_line_ids')
    def _validate_repartition_lines(self):
        for record in self:
            # if the tax is an aggregation of its sub-taxes (group) it can have no repartition lines
            if record.amount_type == 'group' and \
                    not record.invoice_repartition_line_ids and \
                    not record.refund_repartition_line_ids:
                continue

            invoice_repartition_line_ids = record.invoice_repartition_line_ids.sorted(lambda l: (l.sequence, l.id))
            refund_repartition_line_ids = record.refund_repartition_line_ids.sorted(lambda l: (l.sequence, l.id))
            record._check_repartition_lines(invoice_repartition_line_ids)
            record._check_repartition_lines(refund_repartition_line_ids)

            if len(invoice_repartition_line_ids) != len(refund_repartition_line_ids):
                raise ValidationError(_("Invoice and credit note distribution should have the same number of lines."))

            if not invoice_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax') or \
                    not refund_repartition_line_ids.filtered(lambda x: x.repartition_type == 'tax'):
                raise ValidationError(_("Invoice and credit note repartition should have at least one tax repartition line."))

            index = 0
            while index < len(invoice_repartition_line_ids):
                _logger.warning(f"{record=}")
                _logger.warning(f"{invoice_repartition_line_ids[index]=}")
                _logger.warning(f"{refund_repartition_line_ids[index]=}")
                _logger.warning(f"{invoice_repartition_line_ids[index].factor_percent=}")
                _logger.warning(f"{refund_repartition_line_ids[index].factor_percent=}")

                inv_rep_ln = invoice_repartition_line_ids[index]
                ref_rep_ln = refund_repartition_line_ids[index]
                if inv_rep_ln.repartition_type != ref_rep_ln.repartition_type or inv_rep_ln.factor_percent != ref_rep_ln.factor_percent:
                    raise ValidationError(_("Invoice and credit note distribution should match (same percentages, in the same order)."))
                index += 1
            logging.warning(f"{record=}")
            logging.warning(f"{record.name}")
            tax_reps = invoice_repartition_line_ids.filtered(lambda tax_rep: tax_rep.repartition_type == 'tax')
            total_pos_factor = sum(tax_reps.filtered(lambda tax_rep: tax_rep.factor > 0.0).mapped('factor'))
            #if float_compare(total_pos_factor, 1.0, precision_digits=2):
            #    raise ValidationError(_("Invoice and credit note distribution should have a total factor (+) equals to 100."))
            #total_neg_factor = sum(tax_reps.filtered(lambda tax_rep: tax_rep.factor < 0.0).mapped('factor'))
            #if total_neg_factor and float_compare(total_neg_factor, -1.0, precision_digits=2):
            #    raise ValidationError(_("Invoice and credit note distribution should have a total factor (-) equals to 100."))
