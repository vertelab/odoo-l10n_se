from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ocr_control_level = fields.Selection(
        [
            ('soft', 'Soft'),
            ('hard_fixed', 'Hard Fixed'),
        ],
        help="Soft - Only validate Luhn check digit, Hard Fixed - Fixed length, length digit included",
        string='OCR Control Level',
        default='soft',
        config_parameter='l10n_se_ocr.ocr_control_level',
    )
    ocr_fixed_length = fields.Integer(
        string='OCR Fixed Length',
        default=9,
        config_parameter='l10n_se_ocr.ocr_fixed_length',
        help='Total length of the OCR string when using Hard Fixed control level.',
    )
