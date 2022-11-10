from odoo import models, fields, api, _

class AccountRotRut(models.Model):
    _name = "account.rotrut"
    _description = "Accounting Rotrut types"

    skv_code = fields.Char(string='Skatteverkets XML namnkod')
    name = fields.Char(string='Utfört arbete')
    rotrut = fields.Selection([('rut', 'Rut'), ('rot', 'Rot')], string="Typ", default='rut')
