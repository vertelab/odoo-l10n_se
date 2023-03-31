# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression


from odoo.tools import float_compare

_logger = logging.getLogger(__name__)

class Country(models.Model):
    _inherit = 'res.country'

   # get the information that will be injected into the display format
        # get the address format
    address_format = address.country_id.address_format or \
        "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"

class ResCountryForm(models.Model):
    _inherit = "res.country"
    

    def get_address_view_id(self):
        if self.country_id['name'] == 'Sweden':
            return self.address_view_id['name'] == 'view_partner_address_form_swe'
        else:
            return None
    
    