"""Wire demo.dataset to the accounting loader."""
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class DemoDataset(models.Model):
    _inherit = 'demo.dataset'

    def _load_data(self):
        """Load this quarter's moves."""
        self.ensure_one()
        if self.source != 'account':
            return super()._load_data()
        self.env['account.move']._account_demo_load_quarter(self)

    def _unload_data(self):
        """Remove this quarter's moves."""
        self.ensure_one()
        if self.source != 'account':
            return super()._unload_data()
        self.env['account.move']._account_demo_unload_quarter(self)

    def _unreconcile_data(self):
        """Drop payments and reconciliation so the quarter can be matched by hand.

        Order matters: full reconcile first, then partial, then payments,
        then bank statement lines. account.payment refuses to unlink while
        its move is still reconciled.
        """
        self.ensure_one()
        if self.source != 'account':
            return super()._unreconcile_data()
        self.env['account.move']._account_demo_unreconcile_quarter(self)
