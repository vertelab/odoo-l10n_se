# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
##############################################################################

from odoo import models, fields, api, _


class TrainingLesson(models.Model):
    """A single training lesson covering one accounting topic.

    Each lesson combines:
    - System-independent theory (what, why, legal basis)
    - Step-by-step procedure (generic workflow)
    - Odoo-specific practice guide (how to do it in Odoo)
    - SKV references with exact rutor/boxes
    - Self-check questions
    """

    _name = 'l10n_se.training.lesson'
    _description = 'Training Lesson'
    _order = 'category_id, sequence, name'
    _inherit = ['mail.thread']

    name = fields.Char(string='Title', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(default=True)

    category_id = fields.Many2one(
        'l10n_se.training.category', string='Category',
        required=True, ondelete='cascade',
    )

    # Content sections
    overview = fields.Html(
        string='Overview',
        help='What is this lesson about? Why is it important?',
        translate=True,
    )
    theory = fields.Html(
        string='Theory',
        help='System-independent theoretical foundation. '
             'Explain the concept using T-accounts, flow diagrams, '
             'and references to Swedish accounting law (BFL, BFNAR).',
        translate=True,
    )
    procedure = fields.Html(
        string='Procedure',
        help='Generic step-by-step workflow. '
             'System-independent: what to do and in what order, '
             'regardless of which software is used.',
        translate=True,
    )
    odoo_guide = fields.Html(
        string='Odoo Practice Guide',
        help='How to perform this procedure specifically in Odoo. '
             'Include menu paths, screens, field names, and tips.',
        translate=True,
    )

    # SKV / legal references
    skv_reference = fields.Char(
        string='SKV Reference',
        help='Skatteverket guidance reference, e.g. '
             '"SKV 4700 – Momsdeklaration" or "Rättslig vägledning: '
             'Arbetsgivardeklaration".',
    )
    skv_url = fields.Char(string='SKV URL')
    skv_boxes = fields.Char(
        string='SKV Boxes',
        help='Relevant SKV form boxes, e.g. "10, 11, 12, 48, 49" for VAT.',
    )
    bas_accounts = fields.Char(
        string='BAS Accounts',
        help='Relevant BAS accounts for this lesson, e.g. "1510, 1930, 2440, 2610".',
    )
    legal_basis = fields.Text(
        string='Legal Basis',
        help='References to Swedish law: BFL, BFNAR, ÅRL, IL, etc.',
        translate=True,
    )

    # Related Odoo modules
    related_module = fields.Char(
        string='Related Odoo Module',
        help='Technical module name, e.g. "l10n_se_tax_report".',
    )

    # Difficulty
    difficulty = fields.Selection(
        selection=[
            ('beginner', 'Beginner'),
            ('intermediate', 'Intermediate'),
            ('advanced', 'Advanced'),
        ],
        string='Difficulty', default='beginner',
    )
    estimated_minutes = fields.Integer(
        string='Estimated Time (min)', default=15,
    )

    # Progress tracking
    user_progress_ids = fields.One2many(
        'l10n_se.training.progress', 'lesson_id',
        string='User Progress',
    )

    # Self-check
    check_questions = fields.Html(
        string='Self-Check Questions',
        help='Questions the learner should be able to answer after '
             'completing this lesson.',
        translate=True,
    )
    common_mistakes = fields.Html(
        string='Common Mistakes',
        help='Frequent errors and how to avoid them.',
        translate=True,
    )

    # Tags for search
    tag_ids = fields.Many2many(
        'l10n_se.training.tag', string='Tags',
    )

    @api.model
    def _search_by_topic(self, topic):
        """Find lessons matching a topic keyword."""
        return self.search([
            '|', '|',
            ('name', 'ilike', topic),
            ('overview', 'ilike', topic),
            ('theory', 'ilike', topic),
        ])

    def action_mark_complete(self):
        """Mark this lesson as completed for the current user."""
        self.ensure_one()
        progress = self.env['l10n_se.training.progress'].search([
            ('lesson_id', '=', self.id),
            ('user_id', '=', self.env.user.id),
        ], limit=1)
        if not progress:
            self.env['l10n_se.training.progress'].create({
                'lesson_id': self.id,
                'user_id': self.env.user.id,
                'completed': True,
                'completed_date': fields.Datetime.now(),
            })
        else:
            progress.write({
                'completed': True,
                'completed_date': fields.Datetime.now(),
            })

    def action_mark_incomplete(self):
        """Mark this lesson as not completed for the current user."""
        self.ensure_one()
        progress = self.env['l10n_se.training.progress'].search([
            ('lesson_id', '=', self.id),
            ('user_id', '=', self.env.user.id),
        ])
        progress.write({'completed': False, 'completed_date': False})


class TrainingProgress(models.Model):
    """Per-user lesson completion tracking."""

    _name = 'l10n_se.training.progress'
    _description = 'Training Progress'
    _rec_name = 'lesson_id'

    lesson_id = fields.Many2one(
        'l10n_se.training.lesson', string='Lesson',
        required=True, ondelete='cascade',
    )
    user_id = fields.Many2one(
        'res.users', string='User',
        required=True, ondelete='cascade',
        default=lambda self: self.env.user,
    )
    completed = fields.Boolean(string='Completed', default=False)
    completed_date = fields.Datetime(string='Completed On')
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_user_lesson', 'UNIQUE(lesson_id, user_id)',
         'Each user can only have one progress record per lesson.'),
    ]


class TrainingTag(models.Model):
    """Tags for categorizing and searching lessons."""

    _name = 'l10n_se.training.tag'
    _description = 'Training Tag'

    name = fields.Char(string='Tag', required=True)
    color = fields.Integer(string='Color Index', default=0)
