# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 Vertel (<http://vertel.se>).
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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

fromp openerp import netsvc
from openerp import pooler
from openerp.osv import fields, osv
#import decimal_precision as dp
from tools.translate import _

from xml.dom import minidom
import os, base64
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
import tools


class archive_config_installer(osv.osv_memory):
    _name = 'archive_config.installer'
    _inherit = 'res.config.installer'
    _rec_name = 'host'

    def _get_image(self, cr, uid, context=None):
        path = os.path.join('l10n_se','config_pixmaps','module_banner.png')
        image_file = file_data = tools.file_open(path,'rb')
        try:
            file_data = image_file.read()
            return base64.encodestring(file_data)
        finally:
            image_file.close()

    _columns = {
        'msg': fields.text('Message', readonly=True),
        'linkFaqRA':fields.char('Faq arkivering', size=128, help='Vanliga frågor angående arkivering', readonly=True),
        'linkRA':fields.char('Arkivering av räkenskaper', size=128, help='Bokföringsnämnden har i denna vägledning samlat bokföringslagens bestämmelser och nämndens allmänna råd om räkenskapsinformation och dess arkivering (BFNAR 2000:5), kommentarer till dessa samt exempel på hur redovisning kan se ut.', readonly=True),
        'linkFaqAR':fields.char('Faq anläggningsregister', size=128, help='Uttalande om anläggningsregister. Vem är skyldig att upprätta anläggningsregister', readonly=True),
        'linkFAB':fields.char('Enksilda näringsidkare som upprättar förenklat årsbokslut', size=128, help='Bokföringsnämnden (BFN) har i denna vägledning samlat de redovisningsregler som gäller för de flesta enskilda näringsverksamheter. Fysiska personer som upprättar ett förenklat årsbokslut enligt 6 kap. bokföringslagen (1999:1078) ska tillämpa reglerna i vägledningen. Ett sådant får upprättas om nettoomsättningen i företaget normalt uppgår till högst tre miljoner kronor.', readonly=True),        
        'linkAnl':fields.char('Vägledning materiella anläggningstillgångar', size=128, help='Bokföringsnämnden (BFN) har i sina allmänna råd om redovisning av materiella anläggningstillgångar (BFNAR 2001:3) angett hur Redovisningsrådets rekommendation Materiella anläggningstillgångar (RR 12) ska tillämpas i näringsdrivande icke-noterade företag1 som inte valt att tillämpa RR 12.', readonly=True),
        'linkVer':fields.char('Vägledning verifikat', size=128, help='Bokföringsnämnden har i denna vägledning samlat bokföringslagens bestämmelser och nämndens allmänna råd om verifikationer (BFNAR 2000:6)', readonly=True),
        'link28316':fields.char('Anvisningar enskild näringsidkare', size=128, help='Deklarationsanvisningar för enskilda näringsidkare 2012', readonly=True),
        'linkBFN':fields.char('Att föra bok (BFN)', size=128, help='En handledning i bokföring från bokföringsnämnden', readonly=True),
#        'config_logo': fields.binary('Image',readonly=True),        
    }

    def Xdefault_get(self, cr, uid, fields, context=None):
        config_obj = self.pool.get('oo.config')
        data = super(archive_config_installer, self).default_get(cr, uid, fields, context=context)
        ids = config_obj.search(cr, 1, [], context=context)
        if ids:
            res = config_obj.read(cr, 1, ids[0], context=context)
            del res['id']
            data.update(res)
        return data


    _defaults = {
#        'config_logo': _get_image,
        'linkFaqRA':'/l10n_se/static/doc/Rekommendationer för arkivering.pdf',
        'linkRA':'/l10n_se/static/doc/VL00-5-rakenarkiv.pdf',
        'linkFaqAR':'/l10n_se/static/doc/utt03-1.pdf',
        'linkFAB':'/l10n_se/static/doc/VL06-1-enskilda.pdf',
        'linkAnl':'/l10n_se/static/doc/VL01-3-materiellaAT.pdf',
        'linkVer':'/l10n_se/static/doc/VL00-6-verifikationer.pdf',
        'linkBFN':'/l10n_se/static/doc/AttForaBok-12.pdf',
        'link28316':'/l10n_se/static/doc/28316.pdf',
    }

    def install_backup(self,cr,uid,fields,context=None):
        
        
        
        return

archive_config_installer()


class archive_faq(osv.osv_memory):
    _name = 'archive.faq'

    _columns = {
        'sequence':fields.integer('Sequence'),
        'question':fields.char('Question', size=64, required=True),
        'answer':fields.text('Answer', ),
        'link':fields.char('Link', size=128, help='Read more', readonly=True),        
    }

archive_faq()

