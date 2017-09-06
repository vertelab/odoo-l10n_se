# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
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

from openerp import fields, api, models, _

class account_config_settings(models.Model):
    _inherit = 'account.config.settings'

    agd_journal = fields.Many2one(comodel_name='account.journal', string='Arbetsgivardeklaration journal')
    moms_journal = fields.Many2one(comodel_name='account.journal', string='Momsdeklaration journal')

    @api.multi
    def get_default_agd_journal(self):
        return {
            'agd_journal': int(self.env['ir.config_parameter'].get_param('account.agd_journal') or 0),
            'moms_journal': int(self.env['ir.config_parameter'].get_param('account.moms_journal') or 0),
        }

    @api.one
    def set_default_agd_journal(self):
        self.env['ir.config_parameter'].set_param('account.agd_journal', str(self.agd_journal.id))
        self.env['ir.config_parameter'].set_param('account.moms_journal', str(self.moms_journal.id))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
