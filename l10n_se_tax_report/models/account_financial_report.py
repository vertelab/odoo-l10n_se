# -*- coding: utf-8 -*-
# Copyright (C) 2026 Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""A report tree for SRU, on top of account.report.

`account.financial.report` was an Enterprise model that Odoo 18 CE no longer
ships. The SRU export (account.sru.declaration) is built on it: it walks a
tree of nodes, matches move lines per node, and writes each node's
`field_code` into BLANKETTER.SRU.

The Swedish financial reports themselves were ported to `account.report`
(commit 291228a). What was left was this: the SRU side still needs a tree
with per-node SRU metadata — `sru`, `field_code`, `field_code_neg`, `sign`,
`level` — which `account.report.line` does not carry.

So this is deliberately the *smallest* model that satisfies sru.py, not a
reimplementation of the Enterprise one:

    name, parent_id, type, sign, sequence, level,
    account_ids, tax_ids, sru, field_code, field_code_neg, display_detail

It is populated by the SRU import wizard from Skatteverket's own B/R file,
exactly as before. Nothing else reads it.
"""

from odoo import fields, models


class AccountFinancialReport(models.Model):
    _name = 'account.financial.report'
    _description = 'Financial Report (SRU tree)'
    _order = 'sequence, id'
    _parent_store = True

    name = fields.Char(string='Name', required=True, translate=True)
    parent_id = fields.Many2one(
        comodel_name='account.financial.report',
        string='Parent',
        index=True,
        ondelete='cascade',
    )
    parent_path = fields.Char(index=True)
    child_ids = fields.One2many(
        comodel_name='account.financial.report',
        inverse_name='parent_id',
        string='Children',
    )
    type = fields.Selection(
        selection=[
            ('accounts', 'Accounts'),
            ('sum', 'Sum'),
            ('account_type', 'Account Type'),
        ],
        string='Type',
        default='accounts',
        required=True,
        help='"Accounts" is a leaf that holds accounts; "sum" is a heading '
             'whose value comes from its children.',
    )
    sign = fields.Selection(
        selection=[(1, 'Positive'), (-1, 'Negative')],
        string='Sign',
        default=1,
        required=True,
        help='Whether this line adds to or subtracts from its parent.',
    )
    sequence = fields.Integer(default=10)
    level = fields.Integer(
        string='Level',
        compute='_compute_level',
        store=True,
        readonly=False,
    )
    account_ids = fields.Many2many(
        comodel_name='account.account',
        relation='account_financial_report_account_rel',
        column1='report_id',
        column2='account_id',
        string='Accounts',
    )
    tax_ids = fields.Many2many(
        comodel_name='account.tax',
        relation='account_financial_report_tax_rel',
        column1='report_id',
        column2='tax_id',
        string='Taxes',
        help='Lines are matched on tax as well as on account — a VAT report '
             'row is a tax, not an account.',
    )
    sru = fields.Char(
        string='SRU Code',
        help='The SRU box this line feeds, e.g. 3.24. Used by the SRU export '
             'for the 3.26/3.27 profit/loss pair.',
    )
    field_code = fields.Char(
        string='Field Code',
        help='The #UPPGIFT field code written to BLANKETTER.SRU.',
    )
    field_code_neg = fields.Char(
        string='Field Code (negative)',
        help='Field code used when the amount is negative, if the blankett '
             'has a separate box for it.',
    )
    display_detail = fields.Selection(
        selection=[
            ('no_detail', 'No detail'),
            ('detail_flat', 'Detail flat'),
            ('detail_with_hierarchy', 'Detail with hierarchy'),
        ],
        string='Display Detail',
        default='no_detail',
    )

    _sql_constraints = [
        (
            'name_parent_uniq',
            'unique(name, parent_id)',
            'A report line name must be unique within its parent.',
        ),
    ]

    def _compute_level(self):
        for record in self:
            record.level = len(record.parent_path.split('/')) - 2 \
                if record.parent_path else 0
