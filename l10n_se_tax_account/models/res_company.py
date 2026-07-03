# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    # --- Skatteverket API: Tax Account endpoint ---
    skv_skattekonto_api_url = fields.Char(
        string='SKV Tax Account API URL',
        compute='_compute_skv_skattekonto_api_url',
        store=True,
        readonly=False,
        help="Skatteverket API endpoint for tax account transactions.")

    @api.depends('skv_test_mode')
    def _compute_skv_skattekonto_api_url(self):
        for company in self:
            if not company.skv_skattekonto_api_url:
                if company.skv_test_mode:
                    company.skv_skattekonto_api_url = 'https://test.api.skatteverket.se/skattekonto/v2'
                else:
                    company.skv_skattekonto_api_url = 'https://api.skatteverket.se/skattekonto/v2'

    # --- Reconciliation settings ---
    skv_match_tolerance_days = fields.Integer(
        string='Match Tolerance (Days)',
        default=3,
        help="Number of days difference allowed when auto-matching "
             "tax account transactions with booked entries.")
