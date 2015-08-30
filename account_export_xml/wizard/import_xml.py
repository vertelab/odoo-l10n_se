# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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
from openerp import models, fields, api, _
from lxml import etree
import openerp.tools as tools
import openerp.tools.misc as misc
from tempfile import TemporaryFile
import base64



import logging
_logger = logging.getLogger(__name__)


class Wizard(models.TransientModel):
    _name = 'account.export.import'

    data = fields.Binary('File', required=True)

    @api.one
    def load_xml(self,):

        fileobj = TemporaryFile('w+')
        fileobj.write(base64.decodestring(self.data))
        fileobj.seek(0)

        try:
            tools.convert_xml_import(self._cr, 'account_export', fileobj, None, 'init', False, None)

        finally:
            fileobj.close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
