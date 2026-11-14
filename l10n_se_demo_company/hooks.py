"""Post-init: apply the Swedish chart, then create the demo journals.

Order matters. l10n_se_extended applies se_K2 in its own post_init_hook,
but it runs before this module (it is a dependency), so the demo company
does not exist yet when it looks for companies to fix.

We therefore apply the chart ourselves and create the journals afterwards.
account.chart.template.try_loading() unlinks every journal of a company
without existing accounting (chart_template.py:205-217), so the journals
must be created after the chart, never before.
"""
import logging

_logger = logging.getLogger(__name__)

DEFAULT_CHART = 'se_K2'


def _apply_chart(env, company):
    """Apply the Swedish chart to the demo company if it has none."""
    if company.chart_template and company.chart_template != 'generic_coa':
        return company.chart_template
    chart_model = env['account.chart.template']
    if DEFAULT_CHART not in chart_model._get_chart_template_mapping():
        _logger.warning(
            'l10n_se_demo_company: chart %s not available, skipping',
            DEFAULT_CHART)
        return False
    if env['account.move'].search_count([('company_id', '=', company.id)]):
        _logger.info(
            'l10n_se_demo_company: %s already has moves, not applying chart',
            company.name)
        return company.chart_template
    try:
        chart_model.try_loading(DEFAULT_CHART, company, install_demo=False)
    except Exception as exc:  # noqa: BLE001 - a hook must not block install
        _logger.warning(
            'l10n_se_demo_company: could not apply %s: %s', DEFAULT_CHART, exc)
        return False
    company.invalidate_recordset(['chart_template'])
    _logger.info(
        'l10n_se_demo_company: %s chart is now %s',
        company.name, company.chart_template)
    return company.chart_template


def post_init_hook(env):
    company = env.ref('l10n_se_demo_company.company', raise_if_not_found=False)
    if not company:
        _logger.warning('l10n_se_demo_company: demo company not found')
        return
    _apply_chart(env, company)
    env['account.journal']._l10n_se_demo_ensure_journals()
