from odoo import models, fields, api, _

class HelpdeskTicketTeam(models.Model):
    _inherit = 'account.move.line'

    is_rotrut = fields.Boolean(string='Is RotRut')
