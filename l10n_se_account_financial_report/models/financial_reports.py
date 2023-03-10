# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2017 Vertel (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, _
from datetime import date

import logging
_logger = logging.getLogger(__name__)


class FinancialReports(models.Model):
    _name = "financial.reports"
    _description = "financial reports"

    # Har en lista av account.finacial.report.line
    # Har från och till datum.
    start_date= fields.Date(string="Start Date")
    end_date= fields.Date(string="End Date")

    # Har en funktion för att gå igenom alla rader och skriva ut resultatet. For loop

    lines = fields.One2many("financial.reports.line","parent_id")
    

    # def _compute_catsh_lines(self):
    #     for line in self.lines:
    #         # _logger.error(f"{line}")
    #         _logger.error("Hi")

    #byg en lista;logger
    #list view; varige rad har en record(?)
        
