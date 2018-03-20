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
    'name': 'Account Asset Accruals',
    'version': '0.3',
    'category': 'account',
    'summary': 'Short term expense accruals',
    'description': """
        
        An accrual is a journal entry that is used to recognize expenses 
        that will be consumed on several periods and for which the related 
        cash amounts already have been payed. Accruals are needed to ensure
        that the expense are recognized within the correkt reporting period,
        irrespective of the timing the related cash flows.
        
        Accruals are implemented as non prorata temporis assets with a linear
        computation method and a period length under 12 months, time method 
        "number of deprecations", skip draft state. With this module
        Assets will start the deprecating on the 1st of the current month 
        instead of 1st january. 
        
        For an example; the rent invoice for april to june are being payed in april
        and booked at a supplier prepaid expense account, an asset can recude
        that account in april, may and june and charge the account for rent
        each month. In reports the rent are distributed equaly for 
        each month instead of only the month when the payment where done.
        
        This module only handles accruals for expenses, its possible to handle
        accruals for revenues too but there is not possible to initiate the accrual
        asset from a sale order line.
        
        You have to create an asset category for each accrual expense category.

""",
    'author': 'Vertel AB',
    'license': 'AGPL-3',
    'website': 'http://www.vertel.se',
    'depends': ['account_asset'],
    'data': [ 
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
    
}
# vim:expandtab:smartindent:tabstop=4s:softtabstop=4:shiftwidth=4:
