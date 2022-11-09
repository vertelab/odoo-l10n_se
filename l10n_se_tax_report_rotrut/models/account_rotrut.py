from odoo import models, fields, api, _

class AccountRotRut(models.Model):
    _name = "account.rotrut"
    _description = "account.rotrut.typetRut"

    skv_code_id = fields.Many2one('account.rotrut.type', string='Utfört arbete')
    name = fields.Char(string='Beskrivning')
    apartment_number = fields.Char(string='Lägenhetsnummer')
    housing_co_reg_number = fields.Char(string='BRF organisationsnummer')
    property_designation = fields.Char(string='Fastighetsbeteckning')
    rotrut_type = fields.Selection([('rut', 'Rut'), ('rot', 'Rot')], string="Typ", required=True, default='rut')
    
class AccountRotRutType(models.Model):
    _name = "account.rotrut.type"
    _description = "Typ av Rotrut arbete"

    skv_code = fields.Char(string='Utfört arbete')
    name = fields.Char(string='Name')
    rotrut = fields.Selection([('rut', 'Rut'), ('rot', 'Rot')], string="Typ", required=True,)
