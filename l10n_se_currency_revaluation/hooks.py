"""Set the default revaluation accounts on install.

3960 and 7960 are the BAS mirror pair for operating receivables and
payables. They exist in every l10n_se_extended chart after
l10n-se-exchange-account-fix; 7960 was missing from extended_se before it.
"""
import logging

_logger = logging.getLogger(__name__)

GAIN_CODE = '3960'
LOSS_CODE = '7960'


def _account_by_code(env, company, code):
    """Find an account by BAS code, across the code_store keys."""
    env.cr.execute("""
        SELECT aa.id
          FROM account_account aa
          JOIN account_account_res_company_rel rel
            ON rel.account_account_id = aa.id
         WHERE rel.res_company_id = %s
           AND EXISTS (
               SELECT 1 FROM jsonb_each_text(aa.code_store) AS kv(k, v)
                WHERE kv.v = %s)
         LIMIT 1
    """, (company.id, code))
    row = env.cr.fetchone()
    return env['account.account'].browse(row[0]) if row else env['account.account']


def post_init_hook(env):
    for company in env['res.company'].search([]):
        gain = _account_by_code(env, company, GAIN_CODE)
        loss = _account_by_code(env, company, LOSS_CODE)
        if not gain or not loss:
            _logger.info(
                'currency_revaluation: %s has no %s/%s, set the accounts '
                'manually', company.name, GAIN_CODE, LOSS_CODE)
            continue
        if not company.currency_revaluation_gain_account_id:
            company.currency_revaluation_gain_account_id = gain.id
        if not company.currency_revaluation_loss_account_id:
            company.currency_revaluation_loss_account_id = loss.id
        if not company.currency_revaluation_journal_id:
            journal = env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', company.id),
            ], limit=1)
            if journal:
                company.currency_revaluation_journal_id = journal.id
