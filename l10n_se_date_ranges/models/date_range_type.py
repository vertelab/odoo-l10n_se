from datetime import date

from odoo import models, fields


class DateRangeType(models.Model):
    _inherit = 'date.range.type'

    def generate_full_year(self, year, date_start=None, company_id=None):
        """Programmatically generate all date ranges of this type for *year*.

        Args:
            year: Calendar year to generate ranges for.
            date_start: Optional override for the generator start date
                        (e.g. first Monday for week types).
            company_id: Target company; defaults to current company.
        Returns the created ``date.range`` records.
        """
        self.ensure_one()
        if date_start is None:
            date_start = date(year, 1, 1)

        generator = self.env['date.range.generator'].create({
            'date_range_type_id': self.id,
            'date_start': date_start,
            'company_id': company_id or self.env.company.id,
            'name_prefix': self.name + ' ',
            'unit_of_time': self.unit_of_time,
            'duration_count': self.duration_count,
            'name_expr': self.name_expr,
        })
        generator.apply()
        return self.env['date.range'].search([
            ('type_id', '=', self.id),
            ('date_start', '>=', f'{year}-01-01'),
            ('date_start', '<=', f'{year}-12-31'),
        ])
