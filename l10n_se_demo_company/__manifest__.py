{
    'name': 'l10n_se: Demo Company',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_demo_company',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localization',
    'license': 'AGPL-3',
    'summary': 'Shared demo company for accounting and payroll demo data.',
    'description': '''
Demo Company
============

The company that both the accounting demo and the payroll demo write to.

Contains no transactions — only the things that must exist before any
demo data can be loaded: the company, its journals, and (in later steps)
the customers, suppliers and employees.

Features:

    - Extends Odoo: Builds on res.company, account.journal.
    ''',
    # l10n_se_extended applies se_K2 in its post_init_hook and unlinks
    # every journal of a company without existing accounting. Depend on it
    # so our own hook runs after the chart is in place.
    'depends': ['account', 'l10n_se', 'l10n_se_extended'],
    'data': [
        'data/company.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
