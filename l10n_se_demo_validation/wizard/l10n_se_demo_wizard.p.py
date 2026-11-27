# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
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
"""Wizard that installs the Swedish accounting demo data.

Exists because the "Load demo data" link in Settings
(``base.demo_force_install_action``) only loads module ``demo`` XML files —
it never reaches ``account.chart.template._get_demo_data()``.  This wizard
calls ``_install_demo()`` directly, which is the only path that creates the
Swedish journal entries.
"""

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nSeDemoWizard(models.TransientModel):
    _name = 'l10n.se.demo.wizard'
    _description = 'Install Swedish accounting demo data'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    chart_template = fields.Char(
        string='Chart of accounts',
        compute='_compute_chart_template',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        compute='_compute_chart_template',
    )
    is_compatible = fields.Boolean(
        string='Swedish chart',
        compute='_compute_chart_template',
    )

    @api.depends('company_id')
    def _compute_chart_template(self):
        for wizard in self:
            company = wizard.company_id
            wizard.chart_template = company.chart_template or _('none')
            wizard.currency_id = company.currency_id
            wizard.is_compatible = self.env[
                'account.chart.template']._l10n_se_is_swedish(company)

    def action_install(self):
        """Delegate to the chart template, which knows the demo payload."""
        self.ensure_one()
        if not self.is_compatible:
            raise UserError(_(
                'Company "%(company)s" does not use a Swedish chart of '
                'accounts (current: %(chart)s). Install a Swedish chart '
                'first.',
                company=self.company_id.display_name,
                chart=self.chart_template,
            ))
        return self.env[
            'account.chart.template'].action_install_swedish_demo(
                self.company_id)
