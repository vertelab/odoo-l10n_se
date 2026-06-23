# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, SUPERUSER_ID


def set_default_se_initiating_party(env):
    companies = env["res.company"].search([])
    for company in companies:
        if company.country_id.code == "SE" and not company.se_initiating_party_identifier:
            company.se_initiating_party_identifier = company.vat or ""
            company.se_initiating_party_scheme = "BANK"
