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
    'name': 'l10n_se_municipality Swedish Municipalities',
    'summary': 'A list of Swedish Municipalities',
    'author': 'Vertel AB',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'category': 'Accounting',
    'version': '14.0.0.1.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'license': 'AGPL-3',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_municipality_class',
    'images': ['/static/description/banner.png'], # 560x280 px.
    'description': """
	The standard hiearchy of Country states is on the second level in a country. This module adds a third level: Country -> State -> Municipality.\n
	\n
	The module can be used to group res_partners and other objects if it is linked to.\n
	An other similar module is: https://github.com/OCA/partner-contact/tree/14.0/base_location_nuts \n
	\n
	Version 14.0.0.1.0 Added a list of municipalities\n
     """,
    'depends': ['contacts'],
    'init_xml': [],
    'data': [
        'data/res.country.municipality.csv',
        'security/ir.model.access.csv',
        'views/municipality_views.xml',
        'views/partner_views.xml',
        ],
    'demo': [
    ],
    'installable': 'True',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
