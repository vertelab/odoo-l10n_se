import logging
from datetime import date, timedelta

from odoo import api

_logger = logging.getLogger(__name__)

SWEDISH_TYPE_EXTERNAL_IDS = [
    'l10n_se_date_ranges.date_range_type_fiscalyear',
    'l10n_se_date_ranges.date_range_type_quarter',
    'l10n_se_date_ranges.date_range_type_month',
    'l10n_se_date_ranges.date_range_type_week',
]


def _first_monday_of_year(year):
    """Return the Monday of the ISO week that contains January 1st of *year*."""
    jan1 = date(year, 1, 1)
    monday_offset = (jan1.weekday() - 0) % 7
    return jan1 - timedelta(days=monday_offset)


def _generate_swedish_date_ranges(cr, registry):
    """Post-init hook: generate date ranges for all Swedish types.

    - Fiscal year, quarter, month: previous, current, and next year.
    - Week: current year only, starting on Monday.

    Called automatically by Odoo after this module's data has been loaded.
    """
    env = api.Environment(cr, api.SUPERUSER_ID, {})
    current_year = date.today().year

    type_years = {
        'l10n_se_date_ranges.date_range_type_fiscalyear': (
            current_year - 1, current_year, current_year + 1,
        ),
        'l10n_se_date_ranges.date_range_type_quarter': (
            current_year - 1, current_year, current_year + 1,
        ),
        'l10n_se_date_ranges.date_range_type_month': (
            current_year - 1, current_year, current_year + 1,
        ),
        'l10n_se_date_ranges.date_range_type_week': (current_year,),
    }

    for xid in SWEDISH_TYPE_EXTERNAL_IDS:
        date_range_type = env.ref(xid, raise_if_not_found=False)
        if not date_range_type:
            _logger.warning('Date range type %s not found, skipping.', xid)
            continue

        is_week = xid == 'l10n_se_date_ranges.date_range_type_week'

        for year in type_years[xid]:
            existing = env['date.range'].search_count([
                ('type_id', '=', date_range_type.id),
                ('date_start', '>=', f'{year}-01-01'),
                ('date_start', '<=', f'{year}-12-31'),
            ])
            if existing:
                _logger.info(
                    'Skipping generation for type %s year %s '
                    '(%d ranges already exist).',
                    date_range_type.name, year, existing,
                )
                continue

            _logger.info(
                'Generating %s date ranges for year %s.',
                date_range_type.name, year,
            )

            if is_week:
                start = _first_monday_of_year(year)
            else:
                start = date(year, 1, 1)

            date_range_type.generate_full_year(year, date_start=start)
