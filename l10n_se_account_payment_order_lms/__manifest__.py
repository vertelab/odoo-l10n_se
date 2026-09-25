# Copyright (C) 2026 Vertel AB (<https://vertel.se>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'l10n_se: Betalorder och Pending-state — Utbildning (LMS)',
    'version': '18.0.1.0.0',
    'summary': 'Svensk utbildning om betalorder, pending-state och bankavstämning via website_slides',
    'category': 'Accounting/Training',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_account_payment_order_lms',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'description': '''
Betalorder och Pending-state — Utbildning (LMS)
===============================================

    Training material delivered as website_slides courses. 5 sections, 20+ slides
(articles) covering payment orders and the pending state.
    ''',
    'depends': [
        'website_slides',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/slide_channel.xml',
        'data/slide_slides_s1.xml',
        'data/slide_slides_s2.xml',
        'data/slide_slides_s3.xml',
        'data/slide_slides_s4.xml',
        'data/slide_slides_s5.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
