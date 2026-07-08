# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    bankgiro_account_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Bankgiro-konto",
        domain="[('acc_type', '=', 'bgnr'), ('partner_id', '=', company_partner_id)]",
        help="Bankgiro-konto kopplat till denna journal. "
             "Används bara när man vill kunna skicka betalningar "
             "via både Bankgiro och IBAN från samma konto.",
    )
