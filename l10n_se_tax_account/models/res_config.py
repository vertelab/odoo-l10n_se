# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    skv_match_tolerance_days = fields.Integer(
        string='Match Tolerance (Days)',
        related='company_id.skv_match_tolerance_days',
        readonly=False,
        help="Number of days difference allowed when auto-matching "
             "tax account transactions with booked entries.")
