import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class DateRangeGenerator(models.TransientModel):
    _inherit = 'date.range.generator'

    @api.onchange('type_id')
    def _onchange_type_id(self):
        """Pre-fill generator fields from the selected date range type.

        The OCA module already provides _compute_* methods for this,
        but we ensure name_expr flows through explicitly for Swedish types.
        """
        if self.type_id:
            t = self.type_id
            if t.name_expr:
                self.name_expr = t.name_expr
