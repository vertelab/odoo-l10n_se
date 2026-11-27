from datetime import date

from odoo import models, fields


class DateRangeType(models.Model):
    _inherit = 'date.range.type'

    def generate_full_year(self, year, date_start=None, company_id=None):
        """Programmatically generate all date ranges of this type for *year*.

        Args:
            year: Calendar year to generate ranges for.
            date_start: Optional override for the generator start date.
            company_id: Target company; defaults to the type's company.
        Returns the created ``date.range`` records.
        """
        self.ensure_one()
        if date_start is None:
            date_start = date(year, 1, 1)

        generator = self.env['date.range.generator'].create({
            'type_id': self.id,
            'date_start': date_start,
            'company_id': company_id or self.company_id.id,
            'name_expr': self.name_expr,
            'count': 0,
            'date_end': date(year, 12, 31),
            'duration_count': self.duration_count,
            'unit_of_time': self.unit_of_time,
        })
        generator.action_apply()
        return self.env['date.range'].search([
            ('type_id', '=', self.id),
            ('date_start', '>=', f'{year}-01-01'),
            ('date_start', '<=', f'{year}-12-31'),
        ])
