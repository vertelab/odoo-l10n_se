# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'l10n_se: Swedish MIS-reports',
    'version': '14.0.0.0.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Create Swedish MIS-reports',
    'category': 'Accounting',
    'description': """
        The module works as a base for creating Swedish MIS-reports  
        Balansrapportmallen:
        Dessa rubriker innehåller överlappande konton, om dessa används justera enligt de redovisningsriktlinjer som gäller för er verksamhet
        Bakgrunden är att Skatteverket/Bolagsverket anpassar rubrikerna till olika redovisningsprinciper.
        
        - Koncessioner, patent, licenser, varumärken samt liknande rättigheter  och 	Immateriella anläggningstillgångar
        - Andelar i koncernföretag  och Finansiella anläggningstillgångar
        - Lager av råvaror och förnödenheter och Varulager m.m.
        
        Om någon av dessa rubriker används måste konto-listan knuten till rubriken justeras
        
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_mis',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_Se',
    'images': ['static/description/banner.png'], # 560x280 px.
    'depends': ['mis_builder', 'mis_builder_budget', 'account_period'],
    'external_dependencies': {
        'python': ['xlrd'],
    },
    'data': [
        'data/mis_financial_report.xml',
        'data/mis_momsdeklaration_report.xml',
        'data/mis_arbetsgivardeklaration_report.xml',
        'views/mis_report_instance_view.xml',
        'views/mis_template.xml',
        'security/security.xml',
    ],
    'installable': 'True',
    'application': 'False',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
