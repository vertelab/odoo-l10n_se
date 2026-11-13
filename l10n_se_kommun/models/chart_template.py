# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models

import logging

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    """Kommun chart of accounts without interim accounts.

    Same reasoning as ``l10n_se_extended``: the kommun chart is a
    standalone BAS variant (no parent template), so it needs its own
    override. Odoo would otherwise create ``Outstanding Receipts`` and
    ``Outstanding Payments`` in the kommun chart too.

    The kommun chart uses 3-digit codes, so the transfer account is
    ``195 Bank transfer`` — not the 4-digit ``1955`` used by the other
    Swedish charts.

    Note on account types: every account in ``account.account-kommun_bas_se.csv``
    is typed from its kontogrupp per SKR Kommun-Bas 27. The one deliberate
    deviation is 195, which is ``asset_current`` rather than ``asset_cash`` —
    Odoo requires the transfer account to be reconcilable and non-cash, so it
    can never be the same account as 192 Bank.
    """

    _inherit = "account.chart.template"

    _KOMMUN_TEMPLATE = "kommun_bas_se"
    _KOMMUN_TRANSFER_ACCOUNT_CODE = "195"

    _KOMMUN_INTERIM_XMLIDS = (
        "account_journal_payment_debit_account_id",
        "account_journal_payment_credit_account_id",
    )

    def _post_load_data(self, template_code, company, template_data):
        res = super()._post_load_data(template_code, company, template_data)

        if template_code == self._KOMMUN_TEMPLATE:
            self._kommun_drop_interim_accounts(company or self.env.company)

        return res

    def _kommun_drop_interim_accounts(self, company):
        company_sudo = company.sudo()
        root = company_sudo.root_id

        interim_accounts = company_sudo.env["account.account"]
        for xmlid_name in self._KOMMUN_INTERIM_XMLIDS:
            imd = company_sudo.env["ir.model.data"].search(
                [
                    ("module", "=", "account"),
                    ("name", "=", f"{root.id}_{xmlid_name}"),
                    ("model", "=", "account.account"),
                ],
                limit=1,
            )
            if not imd:
                continue
            account = company_sudo.env["account.account"].browse(imd.res_id)
            if account.exists():
                interim_accounts |= account
            imd.unlink()

        if interim_accounts:
            interim_accounts.filtered(lambda a: not a.deprecated).write({"deprecated": True})
            _logger.info(
                "Kommun chart: deprecated interim accounts %s",
                interim_accounts.mapped("code"),
            )

        transfer = company_sudo.env["account.account"].search(
            [
                ("code", "=", self._KOMMUN_TRANSFER_ACCOUNT_CODE),
                ("company_ids", "in", company_sudo.ids),
                ("account_type", "=", "asset_current"),
                ("reconcile", "=", True),
            ],
            limit=1,
        )
        if not transfer:
            _logger.warning(
                "Kommun chart: account %s not found for company %s; "
                "suspense and transfer accounts left untouched.",
                self._KOMMUN_TRANSFER_ACCOUNT_CODE,
                company_sudo.display_name,
            )
            return

        # Odoo also creates a suspense account from the bank prefix and a
        # transfer account from transfer_account_code_prefix. Both are
        # replaced by 195 and deprecated as well.
        old_suspense = company_sudo.account_journal_suspense_account_id
        old_transfer = company_sudo.transfer_account_id
        obsolete = (old_suspense | old_transfer).filtered(
            lambda a: a != transfer
        )

        company_sudo.write(
            {
                "account_journal_suspense_account_id": transfer.id,
                "transfer_account_id": transfer.id,
            }
        )

        journals = company_sudo.env["account.journal"].search(
            [
                ("company_id", "=", company_sudo.id),
                ("type", "in", ("bank", "cash", "credit")),
            ]
        )
        stale = journals.filtered(
            lambda j: not j.suspense_account_id
            or j.suspense_account_id != transfer
        )
        if stale:
            stale.write({"suspense_account_id": transfer.id})

        if obsolete:
            obsolete.filtered(
                lambda a: not a.deprecated
            ).write({"deprecated": True})
            _logger.info(
                "Kommun chart: deprecated interim account(s) %s, "
                "replaced by %s",
                obsolete.mapped("code"),
                transfer.code,
            )
