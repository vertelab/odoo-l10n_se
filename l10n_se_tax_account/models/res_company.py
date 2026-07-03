# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # --- Reconciliation settings ---
    skv_match_tolerance_days = fields.Integer(
        string='Match Tolerance (Days)',
        default=3,
        help="Number of days difference allowed when auto-matching "
             "tax account transactions with booked entries.")
