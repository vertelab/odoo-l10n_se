# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import random


class TrainingQuestion(models.Model):
    """A diagnostic question for a training lesson or category.

    Multiple choice with exactly one correct answer and 3+ distractors.
    Includes explanation shown after answering.
    """

    _name = 'l10n_se.training.question'
    _description = 'Training Question'
    _order = 'category_id, lesson_id, sequence'

    name = fields.Char(string='Question ID', compute='_compute_name', store=True)
    sequence = fields.Integer(string='Sequence', default=10)

    category_id = fields.Many2one(
        'l10n_se.training.category', string='Category',
        ondelete='cascade', index=True,
    )
    lesson_id = fields.Many2one(
        'l10n_se.training.lesson', string='Lesson',
        ondelete='set null', index=True,
        help='Optional — link to a specific lesson.',
    )

    # Question
    question_text = fields.Html(
        string='Question', required=True, translate=True,
    )
    difficulty = fields.Selection(
        selection=[
            ('easy', 'Easy'),
            ('medium', 'Medium'),
            ('hard', 'Hard'),
        ],
        string='Difficulty', default='medium',
    )

    # Answers
    answer_a = fields.Char(string='Answer A', required=True, translate=True)
    answer_b = fields.Char(string='Answer B', required=True, translate=True)
    answer_c = fields.Char(string='Answer C', required=True, translate=True)
    answer_d = fields.Char(string='Answer D', required=True, translate=True)

    correct_answer = fields.Selection(
        selection=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        string='Correct Answer', required=True,
    )

    explanation = fields.Html(
        string='Explanation',
        help='Shown after answering — explains why the correct answer is right '
             'and why the distractors are wrong.',
        translate=True,
    )

    active = fields.Boolean(default=True)

    @api.depends('category_id', 'lesson_id', 'sequence')
    def _compute_name(self):
        for q in self:
            parts = []
            if q.category_id:
                parts.append(q.category_id.name)
            if q.lesson_id:
                parts.append(q.lesson_id.name)
            parts.append('Q%d' % q.sequence)
            q.name = ' / '.join(parts)

    def check_answer(self, answer):
        """Check if the given answer is correct. Returns (bool, explanation)."""
        self.ensure_one()
        return answer == self.correct_answer, self.explanation

    def get_shuffled_answers(self):
        """Return shuffled answer choices as [(key, text), ...]."""
        self.ensure_one()
        answers = [
            ('a', self.answer_a),
            ('b', self.answer_b),
            ('c', self.answer_c),
            ('d', self.answer_d),
        ]
        random.shuffle(answers)
        return answers

    @api.constrains('correct_answer')
    def _check_answers_distinct(self):
        for q in self:
            answers = {q.answer_a, q.answer_b, q.answer_c, q.answer_d}
            if len(answers) < 4:
                raise ValidationError(_('All four answers must be distinct.'))


class TrainingQuizAttempt(models.Model):
    """Records a user's attempt at a diagnostic quiz.

    Each attempt covers one category and contains 5-10 questions.
    Tracks score and detailed answer history.
    """

    _name = 'l10n_se.training.quiz_attempt'
    _description = 'Quiz Attempt'
    _order = 'create_date desc'
    _inherit = ['mail.thread']

    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        default=lambda self: self.env.user,
        ondelete='cascade',
    )
    category_id = fields.Many2one(
        'l10n_se.training.category', string='Category',
        required=True, ondelete='cascade',
    )
    date_started = fields.Datetime(
        string='Started', default=fields.Datetime.now,
    )
    date_completed = fields.Datetime(string='Completed')
    state = fields.Selection(
        selection=[('in_progress', 'In Progress'), ('completed', 'Completed')],
        string='Status', default='in_progress',
    )

    # Questions used in this attempt
    question_count = fields.Integer(string='Questions', default=10)
    line_ids = fields.One2many(
        'l10n_se.training.quiz_attempt.line', 'attempt_id',
        string='Answers',
    )

    # Results
    score = fields.Integer(string='Score', compute='_compute_score', store=True)
    max_score = fields.Integer(string='Max Score', compute='_compute_score', store=True)
    percentage = fields.Float(
        string='Percentage', compute='_compute_score', store=True,
    )

    @api.depends('line_ids', 'line_ids.is_correct')
    def _compute_score(self):
        for attempt in self:
            correct = sum(1 for line in attempt.line_ids if line.is_correct)
            total = len(attempt.line_ids)
            attempt.score = correct
            attempt.max_score = total
            attempt.percentage = (correct / total * 100) if total > 0 else 0.0

    def action_start_quiz(self):
        """Initialize the quiz with random questions from the category."""
        self.ensure_one()
        if self.line_ids:
            return  # Already initialized

        questions = self.env['l10n_se.training.question'].search([
            ('category_id', '=', self.category_id.id),
            ('active', '=', True),
        ])
        if not questions:
            return

        # Pick random subset
        count = min(self.question_count, len(questions))
        selected = questions.random_records(count)

        for q in selected:
            self.env['l10n_se.training.quiz_attempt.line'].create({
                'attempt_id': self.id,
                'question_id': q.id,
            })

    def action_complete_quiz(self):
        """Mark the quiz as completed."""
        self.ensure_one()
        self.state = 'completed'
        self.date_completed = fields.Datetime.now()

    def action_retake(self):
        """Create a new attempt for the same category."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n_se.training.quiz_attempt',
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_category_id': self.category_id.id,
                'default_question_count': self.question_count,
            },
        }


class TrainingQuizAttemptLine(models.Model):
    """One answered question in a quiz attempt."""

    _name = 'l10n_se.training.quiz_attempt.line'
    _description = 'Quiz Answer'
    _order = 'question_id'

    attempt_id = fields.Many2one(
        'l10n_se.training.quiz_attempt', string='Attempt',
        required=True, ondelete='cascade',
    )
    question_id = fields.Many2one(
        'l10n_se.training.question', string='Question',
        required=True, ondelete='cascade',
    )
    answer_given = fields.Selection(
        selection=[('a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D')],
        string='Your Answer',
    )
    is_correct = fields.Boolean(
        string='Correct', compute='_compute_is_correct', store=True,
    )
    answered_at = fields.Datetime(string='Answered At')

    @api.depends('answer_given', 'question_id.correct_answer')
    def _compute_is_correct(self):
        for line in self:
            line.is_correct = (
                line.answer_given and
                line.answer_given == line.question_id.correct_answer
            )

    def action_answer(self, answer):
        """Record the user's answer."""
        self.ensure_one()
        self.answer_given = answer
        self.answered_at = fields.Datetime.now()
