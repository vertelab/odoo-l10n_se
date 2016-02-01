# -*- coding: utf-8 -*-

from openerp import models, fields, api

class Wizard(models.TransientModel):
    _name = 'l10n_se_sie.wizard'

    session_id = fields.Many2one('l10n_se_sie.session',
        string="Session", required=True)
    attendee_ids = fields.Many2many('res.partner', string="Attendees")9
    
