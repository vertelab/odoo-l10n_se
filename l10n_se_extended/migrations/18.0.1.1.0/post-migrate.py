# -*- coding: utf-8 -*-
"""Remove the K-prefixed interim accounts from existing databases.

Background
----------
``l10n_se_extended`` used to set the chart prefixes to ``K2513``/``K2516``/
``K2517`` with ``code_digits = 4``. Odoo then generated six accounts outside
BAS:

    K2513  Bank Suspense Account      asset_current
    K2514  Bank                       asset_cash
    K2515  Outstanding Receipts       asset_current, reconcile
    K2516  Outstanding Payments       asset_current, reconcile
    K2517  Cash                       asset_cash
    K2518  Liquidity Transfer         asset_current, reconcile

The prefixes are now ``1930``/``1910``/``1955`` and the interim accounts are
no longer created (see ``models/chart_template.py``). This migration brings
existing databases in line.

Order is mandatory
------------------
The code that makes ``account.payment._get_outstanding_account()`` survive
without an interim account is shipped in the same version as this migration
(``account_payment_order_pending``). The interim accounts are therefore
removed *after* that code is in place — Odoo loads the registry before
running migrations, so the order holds.

What is done
------------
1. ``K2515``/``K2516`` (Outstanding Receipts/Payments) are deprecated. Their
   xmlids are removed so ``chart_template.ref()`` stops resolving them —
   otherwise ``_get_outstanding_account()`` would keep returning them.
2. ``K2514`` -> ``1930`` and ``K2517`` -> ``1910`` are re-coded with an
   explicit ``write()``. ``reflect_code_prefix_change()`` is **not** used: it
   only touches ``account_type = asset_cash`` and would leave the
   ``asset_current`` accounts behind with a K prefix.
3. ``K2513``/``K2518`` are deprecated and replaced by ``1955``, which becomes
   both ``account_journal_suspense_account_id`` and ``transfer_account_id``.
4. Journals pointing at a deprecated account are re-pointed.

Nothing is deleted: ``account.move.line`` rows may reference these accounts,
and BFL requires the trail to stay intact.
"""
import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Old K-prefixed codes -> new BAS code. ``None`` means "deprecate and replace
# by the transfer account".
RECODE_MAP = {
    "K2514": "1930",  # Bank
    "K2517": "1910",  # Cash
}

DEPRECATE_MAP = {
    "K2513": "1955",  # Bank Suspense Account -> Bank transfer
    "K2515": None,  # Outstanding Receipts -> removed
    "K2516": None,  # Outstanding Payments -> removed
    "K2518": "1955",  # Liquidity Transfer -> Bank transfer
}

TRANSFER_CODE = "1955"
# The kommun chart uses 3-digit codes, so its transfer account is 195.
TRANSFER_CODE_FALLBACKS = ("1955", "195")

INTERIM_XMLIDS = (
    "account_journal_payment_debit_account_id",
    "account_journal_payment_credit_account_id",
)


def migrate(cr, version):
    if not version:
        # Fresh install: nothing to migrate.
        return

    env = api.Environment(cr, SUPERUSER_ID, {})

    Account = env["account.account"].with_context(active_test=False)
    company_model = env["res.company"]

    for company in company_model.search([]):
        _migrate_company(env, Account, company)


def _migrate_company(env, Account, company):
    # Only act when the company still carries K-prefixed accounts. A company
    # created after this version has none and is skipped entirely.
    k_accounts = Account.search(
        [("code", "=like", "K%"), ("company_ids", "in", company.ids)]
    )
    if not k_accounts:
        return

    _logger.info(
        "l10n_se_extended 18.0.1.1.0: migrating interim accounts for %s",
        company.display_name,
    )

    # --- Step 1: drop the interim xmlids ---------------------------------
    root = company.root_id
    for xmlid_name in INTERIM_XMLIDS:
        imd = (
            env["ir.model.data"]
            .sudo()
            .search(
                [
                    ("module", "=", "account"),
                    ("name", "=", f"{root.id}_{xmlid_name}"),
                    ("model", "=", "account.account"),
                ],
                limit=1,
            )
        )
        if imd:
            _logger.info(
                "  removing xmlid account.%s_%s (account %s)",
                root.id,
                xmlid_name,
                env["account.account"].browse(imd.res_id).code,
            )
            imd.unlink()

    # --- Step 2: re-code the liquidity accounts --------------------------
    for old_code, new_code in RECODE_MAP.items():
        account = Account.search(
            [("code", "=", old_code), ("company_ids", "in", company.ids)], limit=1
        )
        if not account:
            continue
        taken = Account.search(
            [("code", "=", new_code), ("company_ids", "in", company.ids)], limit=1
        )
        if taken and taken != account:
            _logger.warning(
                "  %s already exists for %s; leaving %s in place",
                new_code,
                company.display_name,
                old_code,
            )
            continue
        _logger.info("  re-coding %s -> %s", old_code, new_code)
        account.write({"code": new_code})

    # --- Step 3: resolve the transfer account ----------------------------
    # The chart in use decides the code: 1955 for extended_se/K2/K3, 195 for
    # the kommun chart. Both are accepted so the migration works whichever
    # chart the company is on.
    transfer = Account.browse()
    for code in TRANSFER_CODE_FALLBACKS:
        transfer = Account.search(
            [
                ("code", "=", code),
                ("company_ids", "in", company.ids),
                ("account_type", "=", "asset_current"),
                ("reconcile", "=", True),
            ],
            limit=1,
        )
        if transfer:
            break

    if not transfer:
        _logger.warning(
            "  no transfer account (%s) found for %s; "
            "interim accounts left untouched",
            "/".join(TRANSFER_CODE_FALLBACKS),
            company.display_name,
        )
        return

    # --- Step 4: deprecate the interim accounts --------------------------
    to_deprecate = Account.browse()
    for old_code in DEPRECATE_MAP:
        account = Account.search(
            [("code", "=", old_code), ("company_ids", "in", company.ids)], limit=1
        )
        if account:
            to_deprecate |= account

    if to_deprecate:
        _logger.info(
            "  deprecating %s", ", ".join(to_deprecate.mapped("code"))
        )
        to_deprecate.filtered(lambda a: not a.deprecated).write({"deprecated": True})

    # --- Step 5: point the company and journals at 1955 -------------------
    company.sudo().write(
        {
            "account_journal_suspense_account_id": transfer.id,
            "transfer_account_id": transfer.id,
        }
    )

    journals = env["account.journal"].search(
        [("company_id", "=", company.id), ("type", "in", ("bank", "cash", "credit"))]
    )
    stale = journals.filtered(
        lambda j: not j.suspense_account_id
        or j.suspense_account_id.deprecated
        or j.suspense_account_id != transfer
    )
    if stale:
        _logger.info(
            "  re-pointing journals %s to suspense %s",
            ", ".join(stale.mapped("code")),
            transfer.code,
        )
        stale.write({"suspense_account_id": transfer.id})

    # --- Step 6: verify ----------------------------------------------
    remaining = Account.search(
        [("code", "=like", "K%"), ("company_ids", "in", company.ids)]
    )
    still_active = remaining.filtered(lambda a: not a.deprecated)
    if still_active:
        _logger.warning(
            "  K-prefixed accounts still active after migration: %s",
            ", ".join(still_active.mapped("code")),
        )
    else:
        _logger.info("  no active K-prefixed accounts remain")
