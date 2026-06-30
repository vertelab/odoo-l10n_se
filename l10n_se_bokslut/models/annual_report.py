# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import base64
import logging

_logger = logging.getLogger(__name__)


class AccountAnnualReport(models.Model):
    _name = 'account.annual.report'
    _description = 'Annual Report'
    _inherit = ['mail.thread']

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='restrict',
    )
    name = fields.Char(
        string='Name',
        required=True,
        default=lambda self: _('Annual Report'),
    )
    fiscalyear_id = fields.Many2one(
        comodel_name='account.fiscalyear',
        string='Fiscal Year',
        related='bokslut_id.fiscalyear_id',
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        string='Company',
        related='bokslut_id.company_id',
        store=True,
    )
    rule_set = fields.Selection(
        selection=[('K2', 'K2'), ('K3', 'K3')],
        string='Rule Set',
        required=True,
        default='K2',
    )
    pdf_report = fields.Binary(
        string='PDF Report',
        readonly=True,
    )
    pdf_report_filename = fields.Char(
        string='PDF Filename',
        default='arsredovisning.pdf',
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('generated', 'Generated'),
            ('signed', 'Signed'),
            ('submitted', 'Submitted'),
        ],
        string='State',
        default='draft',
    )

    def generate(self):
        """Generate the annual report PDF."""
        self.ensure_one()
        # In a real implementation, this would:
        # 1. Collect SRU data from account.sru.declaration
        # 2. Collect closing data from account.bokslut
        # 3. Build content sections (management report, BR, RR, notes, cash flow)
        # 4. Render QWeb template -> PDF

        # Placeholder: create minimal report
        report_content = _("""ANNUAL REPORT
==============

Company: %(company)s
Fiscal Year: %(fiscalyear)s
Rule Set: %(ruleset)s

This report is generated from Odoo's year-end closing module.

--- MANAGEMENT REPORT ---
The board of directors hereby submits the annual report for fiscal year %(fiscalyear)s.

--- INCOME STATEMENT ---
Refer to SRU report for detailed figures.

--- BALANCE SHEET ---
Refer to SRU report for detailed figures.

--- NOTES ---
Accounting principles follow BFNAR %(ruleset)s.

--- SIGNATURES ---

______________________
""") % {
            'company': self.company_id.name,
            'fiscalyear': self.fiscalyear_id.name if self.fiscalyear_id else '',
            'ruleset': self.rule_set,
        }
        self.pdf_report = base64.b64encode(report_content.encode('utf-8'))
        self.state = 'generated'

    def action_sign(self):
        """Mark report as signed."""
        self.ensure_one()
        self.state = 'signed'

    def action_submit_bolagsverket(self):
        """Submit to Bolagsverket (future API)."""
        self.ensure_one()
        self.state = 'submitted'
