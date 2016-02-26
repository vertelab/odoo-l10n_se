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

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)


import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

import openerp.addons.decimal_precision as dp



class account_asset_asset(models.Model):
    _inherit = 'account.asset.asset'
    _description = 'Asset'

    @api.v7
    def compute_depreciation_board(self, cr, uid, ids, context=None):
        super(account_asset_asset,self).compute_depreciation_board(cr,uid,ids,context=context)
        for asset in self.browse(cr, uid, ids, context=context):
            _logger.warning('Asset %s' % asset)
            if not asset.prorata and asset.method_period < 12:
                # depreciation_date = 1st in purchase month instead of january the 1st
                purchase_date = datetime.strptime(asset.purchase_date, '%Y-%m-%d')
                depreciation_date = datetime(purchase_date.year, purchase_date.month, 1)
                for line in asset.depreciation_line_ids:
                    self.pool.get('account.asset.depreciation.line').write(cr,uid,line.id,{'depreciation_date': depreciation_date.strftime('%Y-%m-%d') })
                    depreciation_date = (datetime(depreciation_date.year, depreciation_date.month, depreciation_date.day) + relativedelta(months=+asset.method_period))



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
