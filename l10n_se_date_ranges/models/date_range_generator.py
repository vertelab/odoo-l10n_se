import logging

from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class DateRangeGenerator(models.TransientModel):
    _inherit = 'date.range.generator'

    name_expr = fields.Char(
        string='Name Expression',
        related='date_range_type_id.name_expr',
        readonly=False,
        help='Python expression evaluated with ``date_start`` to produce the range name.',
    )

    @api.onchange('date_range_type_id')
    def _onchange_date_range_type_id(self):
        """Pre-fill generator fields from the selected Swedish date range type."""
        if self.date_range_type_id:
            t = self.date_range_type_id
            self.unit_of_time = t.unit_of_time
            self.duration_count = t.duration_count
            self.name_prefix = t.name + ' '
            if t.name_expr:
                self.name_expr = t.name_expr

    def _prepare_date_range_vals(self, date_start, date_end, name):
        """Extend range creation values to include the evaluated name expression
        when the type defines ``name_expr``."""
        vals = super()._prepare_date_range_vals(date_start, date_end, name)
        if self.date_range_type_id.name_expr:
            evaluated_name = self._evaluate_name_expr(
                self.date_range_type_id.name_expr, date_start, date_end,
            )
            if evaluated_name:
                vals['name'] = evaluated_name
        return vals

    @api.model
    def _evaluate_name_expr(self, expr, date_start, date_end):
        """Safely evaluate a ``name_expr`` Python expression.

        Only allows access to ``date_start`` and ``date_end`` (datetime.date).
        Returns the string result or None on failure.
        """
        safe_globals = {
            'date_start': date_start,
            'date_end': date_end,
            '__builtins__': {},
        }
        try:
            result = eval(expr, safe_globals)
            return str(result) if result is not None else None
        except Exception:
            _logger.warning(
                'Failed to evaluate name_expr %r for range %s -> %s',
                expr, date_start, date_end,
            )
            return None
