# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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
import logging
_logger = logging.getLogger(__name__)

class account_config_settings(models.TransientModel):
    _inherit = 'account.config.settings'

    agd_journal = fields.Many2one(comodel_name='account.journal', string='Arbetsgivardeklaration journal')
    moms_journal = fields.Many2one(comodel_name='account.journal', string='Momsdeklaration journal')
    accounting_method = fields.Selection(selection=[('cash', 'Kontantmetoden'), ('invoice', 'Fakturametoden'),], default='invoice',string='Redovisningsmetod',help="Ange redovisningsmetod, OBS även företag som tillämpar kontantmetoden skall välja fakturametoden i sista perioden/bokslutsperioden")
    vat_declaration_frequency = fields.Selection(selection=[(1, 'Month'), (3, 'Quarter'),(12, 'Year')], default=3,string='Skattedeklarationsfrekvens',help="Hur stor är momsdeklarationsperioden?")

    @api.multi
    def set_custom_parameters(self):
        config_parameters = self.env['ir.config_parameter']
        if self.agd_journal:
            config_parameters.set_param(key="l10n_se_tax_report.agd_journal", value=str(self.agd_journal.id))
        if self.moms_journal:
            config_parameters.set_param(key="l10n_se_tax_report.moms_journal", value=str(self.moms_journal.id))
        if self.accounting_method:
            config_parameters.set_param(key="l10n_se_tax_report.accounting_method", value=str(self.accounting_method))
        if self.vat_declaration_frequency:
            config_parameters.set_param(key="l10n_se_tax_report.vat_declaration_frequency", value=str(self.vat_declaration_frequency))

    @api.model
    def get_default_custom_parameters(self, fields=None):
        icp = self.env['ir.config_parameter']
        return {
            'agd_journal': int(icp.get_param(key='l10n_se_tax_report.agd_journal', default='0')) or False,
            'moms_journal': int(icp.get_param(key='l10n_se_tax_report.moms_journal', default='0')) or False,
            'accounting_method': icp.get_param(key='l10n_se_tax_report.accounting_method', default='invoice') or False,
            'vat_declaration_frequency': int(icp.get_param(key='l10n_se_tax_report.vat_declaration_frequency', default='3')) or False,
        }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
