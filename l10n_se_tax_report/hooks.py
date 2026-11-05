# Copyright 2026 Vertel Sverige AB (<https://vertel.se>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Configure the tax account (1630) on install/upgrade.

    The VAT declaration moves the net VAT from 2650 to 1630. Without a
    reconcilable tax account the payment can never be matched against the
    declaration, so the account is marked reconcilable here. Databases that
    already have the account configured are left untouched.
    """
    account_model = env["account.account"]
    try:
        accounts = account_model._l10n_se_tax_report_configure_tax_account()
    except Exception:  # noqa: BLE001 - never block an install
        _logger.warning(
            "Could not configure the tax account %s. Configure it manually "
            "from Accounting settings.",
            "1630",
            exc_info=True,
        )
        return
    _logger.info(
        "Tax account configured as reconcilable: %s",
        ", ".join(accounts.mapped("code")),
    )
