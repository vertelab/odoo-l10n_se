# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013-2018 Vertel AB <http://vertel.se>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from odoo import api, models, fields, _

import logging
_logger = logging.getLogger(__name__)


class account_journal(models.Model):
    _inherit = 'account.journal'

    is_dibs = fields.Boolean(string='Is DIBS')
    dibs_user = fields.Char(string='DIBS sftp user')
    dibs_pw = fields.Char(string='DIBS sftp pw')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
