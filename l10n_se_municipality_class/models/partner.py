# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class Partner(models.Model):
    _name = "res.partner"
    _inherit = ['res.partner']

    municipality_id = fields.Many2one(
        comodel_name='res.country.municipality',
        string='Municipality'
    )
