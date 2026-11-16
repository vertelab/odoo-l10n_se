"""Create the demo journals after the chart of accounts is in place.

account.chart.template.try_loading() unlinks every journal of a company
that has no existing accounting (chart_template.py:205-217) before loading
the template. Journals declared in data/ are therefore wiped as soon as
l10n_se_extended applies se_K2 to the demo company.

Creating them from a post_init_hook means they exist after the chart is
loaded, so nothing deletes them afterwards.
"""
import logging

from odoo import models

_logger = logging.getLogger(__name__)

JOURNALS = [
    # xmlid, name, type, code
    ('journal_sale', 'Försäljning', 'sale', 'INV'),
    ('journal_purchase', 'Inköp', 'purchase', 'BILL'),
    ('journal_bank', 'Företagskonto', 'bank', 'BNK1'),
    ('journal_payroll', 'Lönejournal', 'general', 'LÖN'),
    # Source journals from SFA that the demo data references
    ('journal_stock', 'Lagerjournal', 'general', 'STJ'),
    ('journal_misc', 'Diverse', 'general', 'MISC'),
    ('journal_deferred', 'Periodisering', 'general', 'DEF'),
    ('journal_exchange', 'Valutadifferens', 'general', 'EXCH'),
    ('journal_tax', 'Momsjournal', 'general', 'MOMS'),
    ('journal_assets', 'Anläggningstillgångar', 'general', 'ASS'),
    ('journal_cash', 'Kassa', 'cash', 'CSH1'),
    ('journal_warranty', 'Garantidelar', 'general', 'WAR1'),
]


class DemoCompanyJournal(models.Model):
    _inherit = 'account.journal'

    def _l10n_se_demo_ensure_journals(self):
        """Create the demo journals if they are missing. Idempotent."""
        company = self.env.ref('l10n_se_demo_company.company', raise_if_not_found=False)
        if not company:
            return 0
        created = 0
        for xmlid, name, jtype, code in JOURNALS:
            existing = self.search([
                ('code', '=', code),
                ('company_id', '=', company.id),
            ], limit=1)
            if existing:
                continue
            journal = self.create({
                'name': name,
                'type': jtype,
                'code': code,
                'company_id': company.id,
            })
            self.env['ir.model.data'].create({
                'module': 'l10n_se_demo_company',
                'name': xmlid,
                'model': 'account.journal',
                'res_id': journal.id,
                'noupdate': True,
            })
            created += 1

        # The payroll journal needs a default account: OCA's payroll_account
        # uses it for the balancing line when the salary rules do not add up
        # exactly, and raises if it is missing. 7090 is the salary account
        # group's balancing account in se_K2.
        payroll = self.search([
            ('code', '=', 'LÖN'),
            ('company_id', '=', company.id),
        ], limit=1)
        if payroll and not payroll.default_account_id:
            self.env.cr.execute("""
                SELECT aa.id FROM account_account aa
                  JOIN account_account_res_company_rel rel
                    ON rel.account_account_id = aa.id
                 WHERE rel.res_company_id = %s
                   AND EXISTS (
                       SELECT 1 FROM jsonb_each_text(aa.code_store) AS kv(k, v)
                        WHERE kv.v = '7090')
                 LIMIT 1
            """, (company.id,))
            row = self.env.cr.fetchone()
            if row:
                payroll.default_account_id = row[0]

        _logger.info('l10n_se_demo_company: %s journals created', created)
        return created
