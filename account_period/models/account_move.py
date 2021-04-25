# -*- coding: utf-8 -*-
# Copyright 2017 Jarvis (www.odoomod.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import odoo
from odoo import api, models, _, fields, osv
from odoo.osv import expression


class AccountMove(models.Model):
    _inherit = "account.move"

    period_id = fields.Many2one('account.period', 'Period', required=False, states={'posted':[('readonly',True)]})

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    period_id = fields.Many2one('account.period', string='Period', related='move_id.period_id',required=False, index=True,store=True)