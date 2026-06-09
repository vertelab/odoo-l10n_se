# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2026 Vertel AB (<https://vertel.se>)
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name': 'Fix mis_builder annotation init',
    'version': '1.0.0',
    'summary': 'Guard mis.report.instance.annotation.init() against missing table',
    'category': 'Technical',
    'description': """
        Prevents a crash during registry preloading when
        mis_builder mis_report_instance_annotation.init() tries to
        CREATE INDEX on a table that does not yet exist.
    """,
    'author': 'Vertel AB',
    'website': 'https://vertel.se',
    'license': 'AGPL-3',
    'depends': ['mis_builder'],
    'data': [],
    'installable': True,
    'application': False,
    'auto_install': True,
}
