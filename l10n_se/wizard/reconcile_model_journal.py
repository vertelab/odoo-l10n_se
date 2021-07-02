# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2017 Vertel (<http://vertel.se>).
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

class wizard_reconcile_model_journal(models.TransientModel):
    _name = 'wizard.reconcile.model.journal'
    _description = "Wizard Reconcile Model Journal"

    journal_id = fields.Many2one(comodel_name='account.journal', string='Journal', help='')

    @api.multi
    def set_journal(self):
        if self.journal_id:
            for id in self._context.get('active_ids', []):
                self.env['account.reconcile.model'].browse(id).journal_id = self.journal_id


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
