# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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
    'name': 'Swedish electronic tax declaration',
    'version': '0.1',
    'category': 'account',
    'summary': 'Creates files for swedish tax declaration',
    'description': """
Creates files for swedish tax declaration eSDK
==================================


https://www.skatteverket.se/foretagorganisationer/skatter/momsarbetsgivardeklarationerskattedeklaration/forkonstruktorer/dtdfil.4.65fc817e1077c25b83280000.html

Tester:
https://www1.skatteverket.se/es/demoeskd/loggedIn.do

""",
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['l10n_se',],
    'data': [ 'l10n_se_esdk.xml','l10n_se_esdk_data.xml'
    ],
    'application': False,
    'installable': True,
    'auto_install': True,
    
}
# vim:expandtab:smartindent:tabstop=4s:softtabstop=4:shiftwidth=4:
