# -*- coding: utf-8 -*-

from odoo import models, fields


class ProjectTask(models.Model):
    _inherit = 'project.task'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Bokslut',
        ondelete='cascade',
        help='Linked year-end closing.',
    )
    bokslut_section = fields.Selection(
        selection=[
            ('assets', 'Assets'),
            ('liabilities', 'Liabilities & Equity'),
            ('result', 'Result'),
            ('dispositions', 'Dispositions'),
            ('annual_report', 'Annual Report'),
            ('other', 'Other'),
        ],
        string='Section',
        default='other',
    )
    account_ids = fields.Many2many(
        comodel_name='account.account',
        relation='bokslut_task_account_rel',
        column1='task_id',
        column2='account_id',
        string='Related Accounts',
    )
    is_required = fields.Boolean(
        string='Required',
        default=False,
    )
    is_template = fields.Boolean(
        string='Is Template',
        default=False,
        help='Template tasks are copied to new closings.',
    )
