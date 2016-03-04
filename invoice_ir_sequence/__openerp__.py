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
    'name': 'Invoice ir.sequence',
    'version': '0.3',
    'category': 'account',
    'summary': 'Create simple serial numbers using products',
    'description': """
        Create serial numbers on invoice lines using special products.
        When an invoice are opened the action assign new serial numbers from a sequence are performed.
        
        The serial number sequneces are fetched from product.product ("Product variant").

""",
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['account','product'],
    'data': [ 'invoice_ir_sequence.xml',
              'security/ir.model.access.csv',
    ],
    'licence': 'AGPL3.0',
    'application': False,
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4s:softtabstop=4:shiftwidth=4:
