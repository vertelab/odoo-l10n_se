# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel Sverige AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import _, models
from odoo.exceptions import UserError

# Accounts that carry EU goods sales. Box 35 of the periodic compilation is
# defined by the VTEU/VTEU3 TAX, not by these accounts (see BOX_TAXES in
# account_se_tax_report.py). A line on one of these accounts with no tax at
# all is therefore undefined for the report: it silently drops out of the
# declaration. This guard catches that at posting time, where the mistake is
# actually made, instead of leaving it to be discovered weeks later.
EU_GOODS_ACCOUNT_CODES = ('3106', '3108')


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _check_eu_goods_lines_have_tax(self):
        """Refuse to post EU goods revenue that carries no tax code.

        Only lines that *credit* one of the EU goods accounts are checked:
        a debit is a correction/reversal and must stay possible, and the
        check is about revenue leaving the account untagged.

        The guard is per company and can be switched off in
        Settings -> Declaration settings for companies that deliberately
        post corrections on 3106 without a tax code.
        """
        for move in self:
            if not move.company_id.pc_warn_supplied_goods_without_tax:
                continue
            offenders = move.line_ids.filtered(
                lambda l: l.account_id.code in EU_GOODS_ACCOUNT_CODES
                and l.credit > 0.0
                and not l.tax_ids
            )
            if not offenders:
                continue
            details = ', '.join(
                '%s %s' % (line.account_id.code, line.credit)
                for line in offenders
            )
            raise UserError(_(
                "Försäljning till annat EU-land saknar momskod.\n\n"
                "Rad(er) på konto %(details)s krediteras utan momskod. "
                "Fält 35 i periodisk sammanställning definieras av momskoden "
                "VTEU — utan momskod kan raden aldrig hamna i deklarationen.\n\n"
                "Sätt momskod VTEU på raden. Om raden avsiktligt inte hör "
                "till fält 35 (rättelseverifikat, intern omföring), stäng av "
                "varningen under Inställningar → Deklarationsinställningar.",
                details=details,
            ))

    def _post(self, soft=True):
        self._check_eu_goods_lines_have_tax()
        return super()._post(soft=soft)
