
from odoo import api, fields, models


class IntrastatCode(models.Model):
    _inherit = "hs.code"
    
    quantity = fields.Char(string='Quantity')

