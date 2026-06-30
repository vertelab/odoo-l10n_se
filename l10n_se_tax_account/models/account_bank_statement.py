# -*- coding: utf-8 -*-
# Copyright (C) 2024 Vertel AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models
import logging

_logger = logging.getLogger(__name__)


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    skv_last_fetch = fields.Datetime(
        string='Last SKV Fetch',
        readonly=True,
        help="When transactions were last fetched from Skatteverket.")

    skv_ocr_number = fields.Char(
        string='SKV OCR Number',
        readonly=True,
        help="OCR number from the Skatteverket tax account API response.")
