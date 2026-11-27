"""Demo data wizard: load, remove and reconcile quarters.

The wizard is a thin layer over demo.dataset. Everything it does is also
available as a plain method on the model, so an AI agent can call it
without the web interface:

    env['demo.dataset'].action_load_by_name('2026Q2')
    env['demo.dataset'].action_remove_by_name('2026Q2')
    env['demo.dataset'].action_unreconcile_by_name('2026Q2')
    env['demo.dataset'].action_check_divergence()

The wizard adds what the model cannot know: which quarter is next, what a
removal would take with it, and a preview before anything destructive.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SOURCES = [
    ('account', 'Accounting'),
    ('payroll', 'Payroll'),
]


class DemoDataWizard(models.TransientModel):
    _name = 'demo.data.wizard'
    _description = 'Demo data'

    source = fields.Selection(
        SOURCES, required=True, default='account',
        help='Which demo source to act on. Both are loaded through the '
             'same sequence rule.',
    )
    loaded_through = fields.Char(
        compute='_compute_status', readonly=True,
        help='The last quarter loaded for this source.',
    )
    next_quarter = fields.Char(
        compute='_compute_status', readonly=True,
        help='The quarter that may be loaded next.',
    )
    divergence = fields.Char(
        compute='_compute_status', readonly=True,
        help='Set when the sources are loaded to different points.',
    )
    line_ids = fields.One2many(
        'demo.data.wizard.line', 'wizard_id',
    )
    action = fields.Selection(
        [('load', 'Load next quarter'),
         ('remove', 'Remove selected quarter'),
         ('unreconcile', 'Make selected quarter unreconciled'),
         ('reconcile', 'Reconcile selected quarter')],
        required=True, default='load',
    )
    quarter = fields.Many2one(
        'demo.dataset', string='Quarter',
        domain="[('source', '=', source)]",
        help='The quarter to act on. Loading always takes the next one.',
    )
    confirm_remove = fields.Boolean(
        string='I understand that higher quarters are removed too',
        help='Removing a quarter also removes every higher quarter for '
             'the same source. The list below shows what goes.',
    )
    removal_preview = fields.Text(
        compute='_compute_status', readonly=True,
    )

    @api.depends('source', 'quarter')
    def _compute_status(self):
        Dataset = self.env['demo.dataset']
        for wizard in self:
            loaded = Dataset.search([
                ('source', '=', wizard.source),
                ('state', '!=', 'empty'),
            ], order='sequence desc', limit=1)
            wizard.loaded_through = loaded.name if loaded else _('nothing')
            nxt = Dataset.search([
                ('source', '=', wizard.source),
                ('state', '=', 'empty'),
            ], order='sequence', limit=1)
            wizard.next_quarter = nxt.name if nxt else _('none left')

            marks = Dataset._detect_divergence()
            if marks:
                wizard.divergence = ', '.join(
                    f'{src}: {Dataset.search([("source", "=", src), ("sequence", "=", seq)], limit=1).name}'
                    for src, seq in marks.items())
            else:
                wizard.divergence = False

            if wizard.quarter and wizard.quarter.state != 'empty':
                doomed = Dataset.search([
                    ('source', '=', wizard.source),
                    ('sequence', '>=', wizard.quarter.sequence),
                    ('state', '!=', 'empty'),
                ], order='sequence desc')
                wizard.removal_preview = _(
                    'Removing %(name)s also removes: %(list)s',
                    name=wizard.quarter.name,
                    list=', '.join(doomed.mapped('name')) or _('nothing'),
                )
            else:
                wizard.removal_preview = False

    def _compute_lines(self):
        Dataset = self.env['demo.dataset']
        for wizard in self:
            rows = Dataset.search(
                [('source', '=', wizard.source)], order='sequence')
            wizard.line_ids = [(5, 0, 0)] + [
                (0, 0, {
                    'dataset_id': row.id,
                    'name': row.name,
                    'state': row.state,
                    'kind': row.kind,
                    'loaded_at': row.loaded_at,
                })
                for row in rows
            ]

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'line_ids' in fields_list:
            res['line_ids'] = []
        return res

    def action_run(self):
        """Run the selected action. Returns a notification."""
        self.ensure_one()
        Dataset = self.env['demo.dataset']
        if self.action == 'load':
            nxt = Dataset.search([
                ('source', '=', self.source),
                ('state', '=', 'empty'),
            ], order='sequence', limit=1)
            if not nxt:
                raise UserError(_('There is nothing left to load.'))
            nxt.action_load()
            message = _('Loaded %(name)s.', name=nxt.name)
        elif self.action == 'remove':
            if not self.quarter:
                raise UserError(_('Select the quarter to remove.'))
            if not self.confirm_remove:
                raise UserError(_(
                    'Tick the confirmation box. Removing %(name)s also '
                    'removes every higher quarter.',
                    name=self.quarter.name))
            names = Dataset.search([
                ('source', '=', self.source),
                ('sequence', '>=', self.quarter.sequence),
                ('state', '!=', 'empty'),
            ], order='sequence desc').mapped('name')
            self.quarter.action_remove()
            message = _('Removed %(list)s.', list=', '.join(names))
        elif self.action == 'unreconcile':
            if not self.quarter:
                raise UserError(_('Select the quarter to unreconcile.'))
            self.quarter.action_unreconcile()
            message = _('%(name)s is now unreconciled.',
                        name=self.quarter.name)
        else:
            if not self.quarter:
                raise UserError(_('Select the quarter to reconcile.'))
            self.quarter.action_reconcile()
            message = _('%(name)s is reconciled again.',
                        name=self.quarter.name)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {'message': message, 'type': 'success',
                       'next': {'type': 'ir.actions.act_window_close'}},
        }


class DemoDataWizardLine(models.TransientModel):
    _name = 'demo.data.wizard.line'
    _description = 'Demo data quarter'
    _order = 'dataset_id'

    wizard_id = fields.Many2one('demo.data.wizard', required=True,
                                ondelete='cascade')
    dataset_id = fields.Many2one('demo.dataset', required=True)
    name = fields.Char(readonly=True)
    state = fields.Selection(
        [('empty', 'Not loaded'), ('loaded', 'Loaded'),
         ('unreconciled', 'Unreconciled')],
        readonly=True,
    )
    kind = fields.Selection(
        [('reconciled', 'Reconciled'), ('unreconciled', 'Unreconciled'),
         ('future', 'Future')],
        readonly=True,
    )
    loaded_at = fields.Datetime(readonly=True)
