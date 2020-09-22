# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
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
from odoo.exceptions import except_orm, Warning, RedirectWarning
import re

import logging
_logger = logging.getLogger(__name__)

class res_partner(models.Model):
    _inherit = 'res.partner'

    @api.depends('vat')
    def _company_registry(self):
        for partner in self:
            if partner.vat and re.match('SE[0-9]{10}01', partner.vat):
                partner.company_registry = "%s-%s" % (partner.vat[2:8],partner.vat[8:-2])
    @api.depends('company_registry')
    def _set_company_registry(self):
        for partner in self:
            if not partner.company_registry: continue
            if not partner.company_registry[6] == '-': continue
            partner.vat = 'SE' + partner.company_registry[:6] + partner.company_registry[7:] + '01'

    company_registry = fields.Char(compute="_company_registry",inverse='_set_company_registry',string='Company Registry', size=11,readonly=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
