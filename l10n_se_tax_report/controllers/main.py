# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2019 Vertel AB (<http://vertel.se>).
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
from odoo import http
from odoo.http import request
import werkzeug

import logging
_logger = logging.getLogger(__name__)


class Main(http.Controller):

    @http.route(['/account/report/arsredovisning/<model("account.sru.declaration"):declaration>',], type='http', auth='user', website=True)
    def arsredovisning(self, declaration, **post):
        period = '%s - %s' %(declaration.period_start.date_start, declaration.period_stop.date_stop)
        return request.render('l10n_se_tax_report.arsredovisning', {
                'period': period,
            })
