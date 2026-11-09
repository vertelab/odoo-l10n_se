# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class L10nSeEskdMapping(models.Model):
    """Box code -> eSKD element name.

    The eSKD XML is built from this table instead of from a MIS Builder KPI
    name. A Skatteverket DTD revision is then a data change, and the export
    code carries no knowledge of Swedish box numbering.
    """

    _name = 'l10n.se.eskd.mapping'
    _description = 'eSKD element mapping'
    _order = 'sequence, code'

    code = fields.Char(string='Box Code', required=True, index=True,
                       help='The account.report.line code, e.g. se_10.')
    eskd_tag = fields.Char(string='eSKD Element', required=True,
                           help='The XML element name the eSKD DTD expects.')
    description = fields.Char(string='Description')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('code_uniq', 'UNIQUE(code)', 'Each box code may only map to one eSKD element.'),
    ]
