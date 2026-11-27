# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models

import logging

_logger = logging.getLogger(__name__)


class AccountChartTemplate(models.AbstractModel):
    """Swedish chart of accounts without interim accounts.

    Odoo creates two interim accounts for every company at chart load:
    ``Outstanding Receipts`` and ``Outstanding Payments``. They are the
    middle step of the classic payment flow (payment -> interim account ->
    bank statement -> clearing).

    Vertel's Swedish charts do not use that flow. With the
    ``pending_until_reconciliation`` payment strategy nothing is booked
    before the bank confirms the movement, so the interim accounts are
    never written to. They would only show up as permanent zero rows in the
    balance sheet, the SIE export and every MIS report.

    How Odoo reaches them (18.0)::

        # account/models/account_payment.py:974
        account_ref = 'account_journal_payment_debit_account_id' ...
        outstanding_account = (
            chart_template.ref(account_ref, raise_if_not_found=False)
            or self.company_id.transfer_account_id
        )

    The two interim accounts are **not** company fields. They are created
    as bare ``ir.model.data`` records in ``_setup_utility_bank_accounts``
    and found again through ``ref()``. Archiving the account alone is not
    enough — the xmlid still resolves. The xmlid must be removed, and the
    fallback ``transfer_account_id`` must point at a real BAS account.

    ``1955 Bank transfer`` is the only BAS 19xx account that satisfies both
    domains Odoo requires: ``asset_current`` for the suspense account and
    ``asset_current`` + ``reconcile`` for the transfer account.
    ``2999 OBS-konto`` is ``liability_payable`` and cannot be used here —
    it is a year-end account for unclassifiable items, not a working
    account that is emptied at every reconciliation.
    """

    _inherit = "account.chart.template"

    # ``extended_se`` is the parent of ``extended_se_K2`` and
    # ``chart_template_K3``; the template code passed to _post_load_data is
    # the child, so all three are listed.
    _SE_NO_INTERIM_TEMPLATES = ("extended_se", "extended_se_K2", "chart_template_K3")
    _SE_TRANSFER_ACCOUNT_CODE = "1955"

    _SE_INTERIM_XMLIDS = (
        "account_journal_payment_debit_account_id",
        "account_journal_payment_credit_account_id",
    )

    def _post_load_data(self, template_code, company, template_data):
        res = super()._post_load_data(template_code, company, template_data)

        if template_code in self._SE_NO_INTERIM_TEMPLATES:
            self._se_drop_interim_accounts(company or self.env.company)

        return res

    def _se_drop_interim_accounts(self, company):
        """Remove the interim accounts and point suspense/transfer at 1955."""
        company_sudo = company.sudo()
        root = company_sudo.root_id

        interim_accounts = company_sudo.env["account.account"]
        for xmlid_name in self._SE_INTERIM_XMLIDS:
            full_xmlid = f"account.{root.id}_{xmlid_name}"
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

            # Drop the xmlid first: ref() resolves through ir.model.data, so
            # removing it is what actually stops _get_outstanding_account()
            # from finding the account. The account row itself is archived
            # below to preserve BFL traceability.
            _logger.info(
                "Swedish chart %s: removing xmlid %s (account %s)",
                company_sudo.chart_template,
                full_xmlid,
                account.code if account.exists() else "?",
            )
            imd.unlink()

        if interim_accounts:
            interim_accounts.filtered(lambda a: not a.deprecated).write({"deprecated": True})
            _logger.info(
                "Swedish chart %s: deprecated interim accounts %s",
                company_sudo.chart_template,
                interim_accounts.mapped("code"),
            )

        transfer = company_sudo.env["account.account"].search(
            [
                ("code", "=", self._SE_TRANSFER_ACCOUNT_CODE),
                ("company_ids", "in", company_sudo.ids),
                ("account_type", "=", "asset_current"),
                ("reconcile", "=", True),
            ],
            limit=1,
        )
        if not transfer:
            _logger.warning(
                "Swedish chart %s: account %s not found for company %s; "
                "suspense and transfer accounts left untouched.",
                company_sudo.chart_template,
                self._SE_TRANSFER_ACCOUNT_CODE,
                company_sudo.display_name,
            )
            return

        # Odoo also creates a suspense account from the bank prefix
        # (_get_accounts_data_values -> account_journal_suspense_account_id,
        # name "Bank Suspense Account") and a transfer account from
        # transfer_account_code_prefix. Both land on free 193x/195x codes
        # and are interim accounts. They are replaced by 1955 and
        # deprecated as well.
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

        # Odoo assigns the company suspense account to the bank/cash
        # journals right after _setup_utility_bank_accounts(). Those
        # journals still point at the old suspense account, so the
        # assignment is repeated here.
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
                "Swedish chart %s: deprecated interim account(s) %s, "
                "replaced by %s",
                company_sudo.chart_template,
                obsolete.mapped("code"),
                transfer.code,
            )
