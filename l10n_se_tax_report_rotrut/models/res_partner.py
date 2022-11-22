from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'res.partner'

    number_of_rotrut = fields.Integer(string="Rot/Rut fakturor", compute='_rotrut_count')


    def _rotrut_count(self):
        rotrut_count = self.env['account.move'].search(['|', ('partner_id', '=', self.id), ('partner_id', 'in', self.child_ids.ids), ('is_rotrut','=',True)])
        self.number_of_rotrut = len(rotrut_count)

    def rotrut_contact_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rot/Rut fakturor',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': ['|', ('partner_id', '=', self.id), ('partner_id', 'in', self.child_ids.ids), ('is_rotrut','=',True)]
        }
