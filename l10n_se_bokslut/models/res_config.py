# -*- coding: utf-8 -*-

from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    bokslut_rule_set = fields.Selection(
        selection=[('K2', 'K2'), ('K3', 'K3')],
        string='Default Rule Set',
        default='K2',
        help='Default rule set for annual reports (K2 or K3).',
    )
    bokslut_auto_checklist = fields.Boolean(
        string='Auto-Create Checklist',
        default=True,
        help='Automatically create the checklist project when a new closing is created.',
    )
    bokslut_schablon_ranta = fields.Float(
        string='Schablonränta (%)',
        default=2.5,
        help='Statslåneränta for periodization fund schablonintäkt calculation.',
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bokslut_rule_set = fields.Selection(
        related='company_id.bokslut_rule_set',
        readonly=False,
    )
    bokslut_auto_checklist = fields.Boolean(
        related='company_id.bokslut_auto_checklist',
        readonly=False,
    )
    bokslut_schablon_ranta = fields.Float(
        related='company_id.bokslut_schablon_ranta',
        readonly=False,
    )
