# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'l10n_se: AGI — Individual Information (Individuppgifter) + KU',
    'version': '18.0.1.0.0',
    'summary': 'Swedish AGI (Arbetsgivardeklaration individuppgifter) and KU (Kontrolluppgifter) generation',
    'category': 'Accounting',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_agi',
    'license': 'AGPL-3',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'description': """
Swedish AGI — Individual Information (Individuppgifter)
=======================================================
Implements monthly AGI declaration (SKV rutor 50-82) and
KU10 (Kontrolluppgift) for Swedish employers.

Features:
- AGI declaration model inheriting from account.declaration
- Per-employee aggregation from payslips
- Age-based employer fee percentages (<65: 31.42%, 66-79: 16.36%, >=80: 6.15%)
- eSKD XML generation (DTD 6.0)
- SKV API submission via l10n_se_tax_report infrastructure
- KU10 generation
- Växa-stöd support (lower employer fee for first employee)
    """,
    'depends': [
        'l10n_se_tax_report',
        'l10n_se_tax_account',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/agi_declaration_views.xml',
        'views/res_config_view.xml',
        'data/agi_cron_data.xml',
    ],
    'demo': [
        'demo/agi_demo.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
