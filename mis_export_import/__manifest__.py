# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2022- Vertel AB (<https://vertel.se>).
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
    'name': 'MIS Report: Export/Import',
    'version': '16.0.0.0.0',
    'summary': 'Export and Import MIS Report templates with all related data (KPIs, Styles, Queries, etc.)',
    'category': 'Accounting',
    'description': """
        This module allows users to export MIS Report templates to XML files and import them into other Odoo instances.
        It handles:
        * MIS Report Template
        * KPIs and their expressions
        * Styles
        * Queries
        * Subreports
        * Sub-KPIs
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'depends': ['mis_builder', 'l10n_se_mis'],
    "data": [
        "security/ir.model.access.csv",
        "wizards/mis_export_import_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: