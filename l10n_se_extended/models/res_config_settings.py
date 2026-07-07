# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_account_invoice_ai = fields.Boolean(
        string='Document Digitization',
        help='Digitize your PDF or scanned documents using AI. '
             'Installs the account_invoice_ai module for automatic '
             'invoice processing with artificial intelligence.',
    )
