# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2018- Vertel (<http://vertel.se>).
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
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)


class hr_expense(models.Model):
    _inherit = 'hr.expense'

    @api.model
    def _set_supplier_taxes_id(self):
        ii = self.env['account.tax'].search([('name', '=', 'Ii')])
        i12i = self.env['account.tax'].search([('name', '=', 'I12i')])
        if ii and i12i:
            self.env.ref('l10n_se_hr_expense.hotellkostnad').write({'supplier_taxes_id': [(6, 0, [i12i.id])]})
            self.env.ref('l10n_se_hr_expense.parkingsavgifter').write({'supplier_taxes_id': [(6, 0, [ii.id])]})


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
