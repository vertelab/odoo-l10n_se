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

from odoo import fields, api, models, _
import logging
_logger = logging.getLogger(__name__)


class Company(models.Model):
        _inherit = 'res.company'
        ag_contact = fields.Many2many(comodel_name='res.partner', string='Arbetsgivare kontaktperson', domain=[('is_company', '=', False)])
        agd_journal = fields.Many2one(comodel_name='account.journal', string='Arbetsgivardeklaration journal')

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    vat_declaration_frequency = fields.Selection(selection=[('month', 'Month'), ('quarter', 'Quarter'),('year', 'Year')], default='quarter',string='Skattedeklarationsfrekvens',help="Hur stor är momsdeklarationsperioden?",config_parameter='l10n_se_tax_report.vat_declaration_frequency')
