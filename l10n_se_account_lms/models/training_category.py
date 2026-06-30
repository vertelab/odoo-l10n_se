# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
##############################################################################

from odoo import models, fields, api


class TrainingCategory(models.Model):
    """Top-level training category grouping related lessons.

    Examples: Momsredovisning, Bokslut, Bankavstämning, etc.
    """

    _name = 'l10n_se.training.category'
    _description = 'Training Category'
    _order = 'sequence, name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Category', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    description = fields.Html(
        string='Description',
        help='Overview of what this category covers.',
        translate=True,
    )
    icon = fields.Selection(
        selection=[
            ('fa-book', 'Book'),
            ('fa-calculator', 'Calculator'),
            ('fa-file-invoice', 'Invoice'),
            ('fa-balance-scale', 'Balance'),
            ('fa-chart-line', 'Chart'),
            ('fa-landmark', 'Government'),
            ('fa-file-import', 'Import'),
            ('fa-check-double', 'Check'),
            ('fa-graduation-cap', 'Graduation'),
        ],
        string='Icon', default='fa-book',
    )
    color = fields.Integer(string='Color Index', default=0)

    lesson_ids = fields.One2many(
        'l10n_se.training.lesson', 'category_id',
        string='Lessons',
    )
    lesson_count = fields.Integer(
        string='Lessons', compute='_compute_lesson_count',
    )

    # SKV reference
    skv_url = fields.Char(
        string='SKV Reference URL',
        help='Link to Skatteverket guidance for this topic.',
    )

    @api.depends('lesson_ids')
    def _compute_lesson_count(self):
        for rec in self:
            rec.lesson_count = len(rec.lesson_ids)
