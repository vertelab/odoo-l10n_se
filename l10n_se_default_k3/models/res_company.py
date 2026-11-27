# -*- coding: utf-8 -*-
from odoo import models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _l10n_se_apply_default_k3_chart(self):
        """Cron-entrypoint: applicera K3-kontoplanen pa bolag som saknar en."""
        from ..hooks import _apply_default_chart
        _apply_default_chart(self.env, source="l10n_se_default_k3.cron")
        # Cronen ska bara kora en gang - stang av den nar jobbet ar gjort.
        cron = self.env.ref("l10n_se_default_k3.cron_apply_default_chart",
                            raise_if_not_found=False)
        if cron:
            cron.sudo().write({"active": False})
