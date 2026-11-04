# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from .models.account_payment_method import SE_PAYMENT_METHOD_CODES

_logger = logging.getLogger(__name__)

# Default payment modes created for the Swedish (ISO 20022) payment methods.
# A payment method without a payment mode cannot produce a payment order, so
# every installed SE method gets one out of the box. The mode is a starting
# point: the user picks the journal and fills in the bank agreement IDs.
#
#   payment method code, mode name
DEFAULT_MODES = (
    ("se_credit_transfer", "20022 Utbetalning"),
    ("se_credit_transfer_20", "Swedbank MIG 2.0 Utbetalning"),
)


def _first_journal(env, company):
    """Return the company's first bank journal, if any."""
    return env["account.journal"].search(
        [("company_id", "=", company.id), ("type", "=", "bank")],
        limit=1,
    )


def _ensure_payment_modes(env):
    """Make sure every SE payment method has at least one payment mode."""
    method_model = env["account.payment.method"].sudo()
    mode_model = env["account.payment.mode"].sudo()
    company_model = env["res.company"].sudo()

    methods = method_model.search(
        [
            ("code", "in", list(SE_PAYMENT_METHOD_CODES)),
            ("payment_type", "=", "outbound"),
        ]
    )
    if not methods:
        _logger.info(
            "l10n_se_credit_transfer: no Swedish payment methods found, "
            "nothing to link."
        )
        return

    for company in company_model.search([]):
        journal = _first_journal(env, company)
        if not journal:
            _logger.warning(
                "l10n_se_credit_transfer: company '%s' has no bank journal; "
                "create the payment modes for %s manually.",
                company.name,
                ", ".join(m.name for m in methods),
            )
            continue
        for code, mode_name in DEFAULT_MODES:
            method = methods.filtered(lambda m, c=code: m.code == c)[:1]
            if not method:
                continue
            if mode_model.search_count(
                [
                    ("payment_method_id", "=", method.id),
                    ("company_id", "=", company.id),
                ]
            ):
                continue
            mode_model.create(
                {
                    "name": "%s (%s)" % (mode_name, company.name),
                    "payment_method_id": method.id,
                    "company_id": company.id,
                    "bank_account_link": "fixed",
                    "fixed_journal_id": journal.id,
                }
            )
            _logger.info(
                "l10n_se_credit_transfer: created payment mode '%s' for "
                "payment method '%s' (company %s).",
                mode_name,
                method.name,
                company.name,
            )


def post_init_hook(env):
    """Link the Swedish payment methods to a payment mode on install."""
    _ensure_payment_modes(env)
