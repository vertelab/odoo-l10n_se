from dateutil.relativedelta import relativedelta
from odoo.modules.registry import Registry
from odoo.exceptions import RedirectWarning
from odoo import models, fields, api, _
from odoo import http
from odoo.http import request
from odoo import tools

import random

import logging

_logger = logging.getLogger(__name__)

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from datetime import timedelta, date, datetime

import odoo.addons.decimal_precision as dp


# ~ This adds a default credit/debit account field for the account journal, since the fields loss/profit_account_id
# seems to have specific purposes that i don't understand
class account_journal(models.Model):
    _inherit = 'account.journal'

    default_credit_account_id = fields.Many2one(comodel_name='account.account', check_company=True, copy=False,
                                                ondelete='restrict', string='Default Credit Account',
                                                domain=[('deprecated', '=', False)],
                                                )

    default_debit_account_id = fields.Many2one(comodel_name='account.account', check_company=True, copy=False,
                                               ondelete='restrict', string='Default Debit Account',
                                               domain=[('deprecated', '=', False)],
                                               )

    @api.onchange('default_debit_account_id')
    def onchange_debit_account_id(self):
        if not self.default_credit_account_id:
            self.default_credit_account_id = self.default_debit_account_id

    @api.onchange('default_credit_account_id')
    def onchange_credit_account_id(self):
        if not self.default_debit_account_id:
            self.default_debit_account_id = self.default_credit_account_id
