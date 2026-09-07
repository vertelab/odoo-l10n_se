{
    'name': 'l10n_se: Account Demo Data',
'author': 'Vertel Sverige AB',
    'version': '2.8',
    'category': 'Accounting/Localization',
    'license': 'AGPL-3',
    'summary': 'Swedish demo accounting data — journal entries, invoices, partners from Scalinq AB',
    'description': '''
l10n_se Account Demo Data — 1 273 journal entries from Scalinq AB (2023–2025).

Loads on first install via post_init_hook. Resolves accounts and taxes
to l10n_se equivalents automatically — no duplicate chart of accounts.

Data:
- 1273 journal entries + invoices (2023-2025)
- 3 journals (Allmän journal, Leverantörs Betalningar, Bankgiro)
- 11 products
- 110 partners
- 1 fiscal position, 1 payment term
''',
    'depends': ['account', 'l10n_se'],
    'data': [
        'data/account_demo.xml',
    ],
    'demo': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
