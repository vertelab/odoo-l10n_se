# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models



class ReportIntrastatCode(models.Model):
    _inherit = "report.intrastat.code"

    quantity = fields.Char(string='Quantity')


