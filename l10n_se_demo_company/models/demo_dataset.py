"""Demo dataset: one row per quarter and source.

Both the accounting demo and the payroll demo load their data quarter by
quarter. This model owns the sequence rule so neither module has to
reimplement it:

    load(quarter)   only the next quarter may be loaded
    remove(quarter) takes the quarter and every higher one with it

The rule is a stack, not a set — gaps are not allowed.
"""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

SOURCES = [
    ('account', 'Accounting'),
    ('payroll', 'Payroll'),
]

KINDS = [
    ('reconciled', 'Reconciled'),
    ('unreconciled', 'Unreconciled'),
    ('future', 'Future'),
]

STATES = [
    ('empty', 'Not loaded'),
    ('loaded', 'Loaded'),
    ('unreconciled', 'Unreconciled'),
]

# 2023Q4 .. 2027Q4. SFA's accounting data starts 2023-10-31, so the
# dataset starts there: 2022 and earlier 2023 do not exist in the source.
QUARTERS = [(2023, 4)] + [
    (year, quarter)
    for year in (2024, 2025, 2026, 2027)
    for quarter in (1, 2, 3, 4)
]


def sequence_of(year, quarter):
    """1-based position in the 2023Q4..2027Q4 line. 2023Q4 is 1."""
    if (year, quarter) == (2023, 4):
        return 1
    return 1 + (year - 2024) * 4 + quarter


def kind_of(year, quarter):
    """Reconciled through 2026Q1, unreconciled 2026Q2-Q4, future 2027."""
    if (year, quarter) <= (2026, 1):
        return 'reconciled'
    if year == 2026:
        return 'unreconciled'
    return 'future'


class DemoDataset(models.Model):
    _name = 'demo.dataset'
    _description = 'Demo dataset'
    _order = 'source, sequence'

    name = fields.Char(required=True, index=True)
    year = fields.Integer(required=True)
    quarter = fields.Selection(
        [('1', 'Q1'), ('2', 'Q2'), ('3', 'Q3'), ('4', 'Q4')],
        required=True,
    )
    sequence = fields.Integer(
        required=True,
        help='Position in the 2023Q4..2027Q4 line. 2023Q4 is 1, 2027Q4 is 17.',
    )
    source = fields.Selection(SOURCES, required=True, index=True)
    kind = fields.Selection(KINDS, required=True, default='reconciled')
    state = fields.Selection(STATES, required=True, default='empty')
    loaded_at = fields.Datetime(readonly=True)

    _sql_constraints = [  # noqa: RUF012 - Odoo class attribute
        ('sequence_source_uniq', 'unique(source, sequence)',
         'The sequence must be unique per source.'),
        ('name_source_uniq', 'unique(source, name)',
         'The dataset name must be unique per source.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') and vals.get('year') and vals.get('quarter'):
                vals['name'] = f"{vals['year']}Q{vals['quarter']}"
        return super().create(vals_list)

    @api.constrains('sequence', 'year', 'quarter')
    def _check_sequence_matches_quarter(self):
        for rec in self:
            if rec.year and rec.quarter:
                expected = sequence_of(rec.year, int(rec.quarter))
                if rec.sequence != expected:
                    raise ValidationError(_(
                        'Sequence %(seq)s does not match %(name)s '
                        '(expected %(exp)s).',
                        seq=rec.sequence, name=rec.name, exp=expected,
                    ))

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _next_to_load(self):
        """Return the dataset that may be loaded next, or an empty recordset."""
        self.ensure_one()
        loaded = self.search([
            ('source', '=', self.source),
            ('state', '!=', 'empty'),
        ], order='sequence desc', limit=1)
        threshold = loaded.sequence if loaded else 0
        return self.search([
            ('source', '=', self.source),
            ('sequence', '>', threshold),
        ], order='sequence', limit=1)

    def action_load(self):
        """Load this dataset, enforcing the sequence rule."""
        for rec in self:
            if rec.state != 'empty':
                raise UserError(_(
                    '%(name)s is already loaded.', name=rec.name))
            expected = rec._next_to_load()
            if expected != rec:
                if expected:
                    raise UserError(_(
                        'Load %(expected)s first. The datasets are loaded in '
                        'order — %(name)s cannot be loaded before it.',
                        expected=expected.name, name=rec.name))
                raise UserError(_(
                    'There is nothing left to load for %(source)s.',
                    source=rec.source))
            rec._load_data()
            rec.write({
                'state': 'loaded',
                'loaded_at': fields.Datetime.now(),
            })
            _logger.info('demo.dataset: loaded %s/%s', rec.source, rec.name)
        return True

    def _load_data(self):
        """Hook for the module that owns this source. No-op by default."""
        self.ensure_one()
        _logger.info(
            'demo.dataset: no loader for source %s, %s marked loaded',
            self.source, self.name)

    # ------------------------------------------------------------------
    # Removal
    # ------------------------------------------------------------------

    def action_remove(self):
        """Remove this dataset and every higher one for the same source."""
        for rec in self:
            if rec.state == 'empty':
                raise UserError(_(
                    '%(name)s is not loaded.', name=rec.name))
            doomed = self.search([
                ('source', '=', rec.source),
                ('sequence', '>=', rec.sequence),
                ('state', '!=', 'empty'),
            ], order='sequence desc')
            for ds in doomed:
                ds._unload_data()
                ds.write({'state': 'empty', 'loaded_at': False})
                _logger.info(
                    'demo.dataset: removed %s/%s', ds.source, ds.name)
        return True

    def _unload_data(self):
        """Hook for the module that owns this source. No-op by default."""
        self.ensure_one()

    def action_unreconcile(self):
        """Drop payments and reconciliation so the quarter can be matched by hand."""
        for rec in self:
            if rec.state != 'loaded':
                raise UserError(_(
                    '%(name)s is not loaded.', name=rec.name))
            rec._unreconcile_data()
            rec.write({'state': 'unreconciled'})
        return True

    def _unreconcile_data(self):
        """Hook for the module that owns this source. No-op by default."""
        self.ensure_one()

    # ------------------------------------------------------------------
    # Reconciling again
    # ------------------------------------------------------------------

    def action_reconcile(self):
        """Reconcile an unreconciled quarter from its statement files."""
        for rec in self:
            if rec.state != 'unreconciled':
                raise UserError(_(
                    '%(name)s is not unreconciled.', name=rec.name))
            rec._reconcile_data()
            rec.write({'state': 'loaded'})
        return True

    def _reconcile_data(self):
        """Hook for the module that owns this source. No-op by default."""
        self.ensure_one()

    # ------------------------------------------------------------------
    # Plain methods for callers without a web interface
    # ------------------------------------------------------------------

    @api.model
    def action_load_by_name(self, name, source=None):
        """Load a quarter by name. Returns a result dict.

        Used by AI agents and tests: no wizard, no web interface.
        """
        rec = self._by_name(name, source)
        rec.action_load()
        return {
            'quarter': rec.name,
            'source': rec.source,
            'state': rec.state,
            'loaded_through': self.search([
                ('source', '=', rec.source),
                ('state', '!=', 'empty'),
            ], order='sequence desc', limit=1).name,
        }

    @api.model
    def action_remove_by_name(self, name, source=None):
        """Remove a quarter and everything above it. Returns what went."""
        rec = self._by_name(name, source)
        doomed = self.search([
            ('source', '=', rec.source),
            ('sequence', '>=', rec.sequence),
            ('state', '!=', 'empty'),
        ], order='sequence')
        names = doomed.mapped('name')
        rec.action_remove()
        return {
            'removed': names,
            'loaded_through': self.search([
                ('source', '=', rec.source),
                ('state', '!=', 'empty'),
            ], order='sequence desc', limit=1).name or False,
        }

    @api.model
    def action_unreconcile_by_name(self, name, source=None):
        """Make a quarter unreconciled. Returns the new state."""
        rec = self._by_name(name, source)
        rec.action_unreconcile()
        return {'quarter': rec.name, 'state': rec.state}

    @api.model
    def action_reconcile_by_name(self, name, source=None):
        """Reconcile a quarter again. Returns the new state."""
        rec = self._by_name(name, source)
        rec.action_reconcile()
        return {'quarter': rec.name, 'state': rec.state}

    @api.model
    def _by_name(self, name, source=None):
        """Find one dataset by name, optionally scoped to a source."""
        domain = [('name', '=', name)]
        if source:
            domain.append(('source', '=', source))
        matches = self.search(domain)
        if not matches:
            raise UserError(_('No demo dataset named %s.', name))
        if len(matches) > 1:
            raise UserError(_(
                '%s exists for several sources (%s) — pass source.',
                name, ', '.join(matches.mapped('source'))))
        return matches

    # ------------------------------------------------------------------
    # Divergence between sources
    # ------------------------------------------------------------------

    @api.model
    def _source_watermark(self, source):
        """Highest loaded sequence for a source, 0 if nothing is loaded."""
        rec = self.search([
            ('source', '=', source),
            ('state', '!=', 'empty'),
        ], order='sequence desc', limit=1)
        return rec.sequence if rec else 0

    @api.model
    def _detect_divergence(self):
        """Report sources that are loaded to different points.

        Returns a dict {source: watermark} when the installed sources
        diverge, otherwise an empty dict.
        """
        installed = set()
        if 'l10n_se_account_demo' in self.env.registry:
            installed.add('account')
        if 'l10n_se_payroll_demo' in self.env.registry:
            installed.add('payroll')
        if len(installed) < 2:
            return {}
        marks = {src: self._source_watermark(src) for src in installed}
        if len(set(marks.values())) <= 1:
            return {}
        return marks

    @api.model
    def action_check_divergence(self):
        """Raise when the sources are out of step, otherwise report OK."""
        marks = self._detect_divergence()
        if not marks:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'message': _('Sources are in step.'),
                               'type': 'success'}}
        detail = ', '.join(
            f"{src}: {self.search([('source','=',src),('sequence','=',seq)], limit=1).name}"
            for src, seq in marks.items())
        raise UserError(_(
            'The demo sources are loaded to different points (%(detail)s). '
            'Load the lagging source to catch up.', detail=detail))
