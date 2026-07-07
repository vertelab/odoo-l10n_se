# -*- coding: utf-8 -*-
# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    intrastat_arrivals = fields.Selection(
        related="company_id.intrastat_arrivals", readonly=False,
    )
    intrastat_dispatches = fields.Selection(
        related="company_id.intrastat_dispatches", readonly=False,
    )
    intrastat_region_id = fields.Many2one(
        related="company_id.intrastat_region_id", readonly=False,
    )
    intrastat_transport_id = fields.Many2one(
        related="company_id.intrastat_transport_id", readonly=False,
    )
    intrastat_accessory_costs = fields.Boolean(
        related="company_id.intrastat_accessory_costs", readonly=False,
    )
    intrastat_contact_name = fields.Char(
        related="company_id.intrastat_contact_name", readonly=False,
    )
    intrastat_contact_phone = fields.Char(
        related="company_id.intrastat_contact_phone", readonly=False,
    )
    intrastat_contact_email = fields.Char(
        related="company_id.intrastat_contact_email", readonly=False,
    )
    intrastat_remind_user_ids = fields.Many2many(
        related="company_id.intrastat_remind_user_ids", readonly=False,
    )
