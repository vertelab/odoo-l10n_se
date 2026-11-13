# -*- coding: utf-8 -*-
"""Remove the orphaned Swedish Accounting settings view.

Background
----------
``l10n_se_extended`` used to ship
``views/res_config_settings_views.xml`` with a settings hub that toggled
``module_account_period_vrtl``. Two things then happened:

1. ``e166e14`` (2026-10-30) dropped the view from the manifest.
2. ``15a8e8f`` (2026-10-30) deleted the XML file itself.

Neither touches a database that already loaded the view. The ``ir_ui_view``
row stays, and because the manifest no longer lists it, nothing can ever
update or remove it from code. It is a permanent orphan.

Why it blocks an upgrade
------------------------
The stale ``arch_db`` still contains
``<field name="module_account_period_vrtl"/>``. Odoo only creates the
``module_*`` field for a module that is *uninstalled and installable*.
``account_period_vrtl`` is ``installable: False`` since it was retired on
2026-07-08, so the field does not exist -- and any later view that inherits
the settings form fails to parse:

    ParseError: Field "module_account_period_vrtl" does not exist in
    model "res.config.settings"

That is what stops ``repo_apply`` on a database that ran the old view.

What this does
--------------
Deletes the orphaned view rows. The view has no code that recreates it, so
nothing is lost that the module still owns -- but a database may carry manual
edits made in the UI, so the arch is logged before the row goes. The log line
is the only record; if an edit turns out to matter, restore it from there.

Only rows whose arch mentions ``module_account_period_vrtl`` are touched, and
only on ``res.config.settings``. Any other view is left alone.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        # Fresh install: the view was never loaded, nothing to clean.
        return

    cr.execute("""
        SELECT id, name, arch_db::text
        FROM ir_ui_view
        WHERE model = 'res.config.settings'
          AND arch_db::text LIKE '%module_account_period_vrtl%'
    """)
    rows = cr.fetchall()
    if not rows:
        _logger.info(
            "l10n_se_extended 18.0.1.3.0: no orphaned settings view found.")
        return

    for view_id, name, arch in rows:
        _logger.warning(
            "l10n_se_extended 18.0.1.3.0: removing orphaned settings view "
            "id=%s name=%r. Its arch follows, in case it carried manual "
            "edits:\n%s", view_id, name, arch,
        )

    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE model = 'res.config.settings'
          AND arch_db::text LIKE '%module_account_period_vrtl%'
    """)
    _logger.info(
        "l10n_se_extended 18.0.1.3.0: removed %d orphaned settings view(s).",
        len(rows),
    )
