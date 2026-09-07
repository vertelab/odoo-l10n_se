# Copyright (C) 2026 Vertel AB (<https://vertel.se>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'l10n_se: Betalorder och Pending-state — Utbildning (LMS)',
    'version': '18.0.1.0.0',
    'summary': 'Svensk utbildning om betalorder, pending-state och bankavstämning via website_slides',
    'category': 'Accounting/Training',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'description': """
Betalorder och Pending-state — Utbildning (LMS)
================================================
Training material delivered as website_slides courses.

5 sections, 20+ slides (articles, infographics, Mermaid diagrams, quizzes):

- **Section 1:** Introduktion till betalningar i Odoo
  Olika betalsätt, SEPA vs Bankgiro vs Autogiro, BAS-konton.

- **Section 2:** Betalorder — grunderna
  account.payment.method vs account.payment.mode, betalorderns livscykel,
  när blir fakturan betald? (T-konto + mermaid)

- **Section 3:** Pending-state — varför och hur?
  Problemet med tidig matchning, nytt flöde med pending_until_reconciliation,
  jämförelse före/efter (T-konto + mermaid)

- **Section 4:** Praktisk guide — fyra betaltyper
  IBAN, Bankgiro, Autogiro, Manuell betalning — steg för steg med demo.
  Bankavstämning som avslutar flödet.

- **Section 5:** Konfiguration och automatisering
  Supplier Payment Mode, aktivera pending-state i settings, tips för löpande arbete.

5 quiz-slides med 5 frågor var — totalt 25 frågor.
    """,
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
