import logging
from datetime import date, timedelta

_logger = logging.getLogger(__name__)

# The four Swedish date range types, by xmlid in THIS module.
SWEDISH_TYPE_EXTERNAL_IDS = [
    'l10n_se_account_fiscal_year.date_range_type_fiscalyear',
    'l10n_se_account_fiscal_year.date_range_type_quarter',
    'l10n_se_account_fiscal_year.date_range_type_month',
    'l10n_se_account_fiscal_year.date_range_type_week',
]

# Types inherited from the retired l10n_se_date_ranges module. On an upgraded
# database the four types already exist with those xmlids, so the records
# created here would collide on (name, company_id). The hook re-points the
# ir.model.data rows instead of duplicating the types.
LEGACY_MODULE = 'l10n_se_date_ranges'


def _first_monday_of_year(year):
    """Return the Monday of the ISO week that contains January 1st of *year*."""
    jan1 = date(year, 1, 1)
    return jan1 - timedelta(days=jan1.weekday())


def _adopt_legacy_types(env):
    """Re-point l10n_se_date_ranges' date.range.type xmlids to this module.

    An upgraded database has the four types already, owned by the retired
    module. Creating them again raises UniqueViolation on
    date_range_type_date_range_type_uniq. Instead we move the ir.model.data
    row to this module, so env.ref() finds them under the new xmlid and the
    data file's <record> updates the existing rows.

    Returns the number of types adopted.
    """
    Imd = env['ir.model.data'].sudo()
    adopted = 0
    for xid in SWEDISH_TYPE_EXTERNAL_IDS:
        name = xid.split('.', 1)[1]
        legacy = Imd.search([
            ('module', '=', LEGACY_MODULE),
            ('name', '=', name),
            ('model', '=', 'date.range.type'),
        ], limit=1)
        if not legacy:
            continue
        # Only adopt when this module does not already own the xmlid.
        already = Imd.search([
            ('module', '=', 'l10n_se_account_fiscal_year'),
            ('name', '=', name),
            ('model', '=', 'date.range.type'),
        ], limit=1)
        if already:
            continue
        legacy.write({'module': 'l10n_se_account_fiscal_year'})
        adopted += 1
        _logger.info(
            'Adopted date range type %s from %s (res_id %s).',
            name, LEGACY_MODULE, legacy.res_id)
    return adopted


def _pre_init_adopt_legacy_types(env):
    """pre_init_hook: adopt l10n_se_date_ranges' date.range.type xmlids.

    This MUST run before the data file, otherwise
    data/date_range_type_data.xml tries to create a second set of the four
    types and PostgreSQL rejects it on
    date_range_type_date_range_type_uniq (name, company_id).

    A pre_init hook receives the env before the module's data is loaded,
    which is exactly the window we need.
    """
    adopted = _adopt_legacy_types(env)
    _logger.info(
        'l10n_se_account_fiscal_year pre_init: adopted %d legacy date range '
        'type(s).', adopted)


def _generate_swedish_date_ranges(env):
    """Post-init hook: generate date ranges for all Swedish types.

    - Fiscal year, quarter, month: previous, current, and next year.
    - Week: current year only, starting on Monday.

    Idempotent: a year that already has ranges is skipped.
    """
    # Adoption already happened in pre_init_hook; calling again is a no-op
    # but keeps a manual `_generate_swedish_date_ranges` call safe.
    _adopt_legacy_types(env)

    current_year = date.today().year

    type_years = {
        'l10n_se_account_fiscal_year.date_range_type_fiscalyear': (
            current_year - 1, current_year, current_year + 1,
        ),
        'l10n_se_account_fiscal_year.date_range_type_quarter': (
            current_year - 1, current_year, current_year + 1,
        ),
        'l10n_se_account_fiscal_year.date_range_type_month': (
            current_year - 1, current_year, current_year + 1,
        ),
        'l10n_se_account_fiscal_year.date_range_type_week': (current_year,),
    }

    for xid in SWEDISH_TYPE_EXTERNAL_IDS:
        date_range_type = env.ref(xid, raise_if_not_found=False)
        if not date_range_type:
            _logger.warning('Date range type %s not found, skipping.', xid)
            continue

        is_week = xid == 'l10n_se_account_fiscal_year.date_range_type_week'

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
