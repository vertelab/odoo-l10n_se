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
from openerp.exceptions import except_orm, Warning, RedirectWarning

from datetime import datetime


import logging
_logger = logging.getLogger(__name__)


class account_fiscalyear(models.Model):
    _inherit = "account.fiscalyear"

    def _sum_parent_id(self,parent,posted=False):
        #~ raise Warning(self.env['account.account'].search([('code','=',parent)]))
        parent_id = self.env['account.account'].search([('code','=',parent)])[0].id
        #context = str({'fiscalyear': self.id, 'periods': self.period_ids.filtered(lambda p: p.special == False).mapped('id'), 'state': 'posted' if posted else 'all'})
        parent_sum = sum(self.env['account.account'].with_context(fiscalyear=self.id, periods=self.period_ids.filtered(lambda p: p.special == False).mapped('id'), state='posted' if posted else 'all').search([('parent_id','=',parent_id)]).mapped('balance'))
        return str(int(round(parent_sum))) if parent_sum > 0 else ''
        
    company_registry = fields.Char(related='company_id.company_registry')
    f101 = fields.Char(string="1.1 Överskott")
    f102 = fields.Char(string="1.2 Underskott")
        
    @api.one
    def _f201(self):
        self.f201 = self._sum_parent_id('2.1')
    f201 = fields.Char(compute="_f201")
    @api.one
    def _f202(self):
        self.f202 = self._sum_parent_id('2.2')
    f202 = fields.Char(compute="_f202")
    @api.one
    def _f203(self):
        self.f203 = self._sum_parent_id('2.3')
    f203 = fields.Char(compute="_f203")
    @api.one
    def _f204(self):
        self.f204 = self._sum_parent_id('2.4')
    f204 = fields.Char(compute="_f204")
    @api.one
    def _f205(self):
        self.f205 = self._sum_parent_id('2.5')
    f205 = fields.Char(compute="_f205")
    @api.one
    def _f206(self):
        self.f206 = self._sum_parent_id('2.6')
    f206 = fields.Char(compute="_f206")
    @api.one
    def _f207(self):
        self.f207 = self._sum_parent_id('2.7')
    f207 = fields.Char(compute="_f207")
    @api.one
    def _f208(self):
        self.f208 = self._sum_parent_id('2.8')
    f208 = fields.Char(compute="_f208")
    @api.one
    def _f209(self):
        self.f209 = self._sum_parent_id('2.9')
    f209 = fields.Char(compute="_f209")
    @api.one
    def _f210(self):
        self.f210 = self._sum_parent_id('2.10')
    f210 = fields.Char(compute="_f210")
    @api.one
    def _f211(self):
        self.f211 = self._sum_parent_id('2.11')
    f211 = fields.Char(compute="_f211")
    @api.one
    def _f212(self):
        self.f212 = self._sum_parent_id('2.12')
    f212 = fields.Char(compute="_f212")
    @api.one
    def _f213(self):
        self.f213 = self._sum_parent_id('2.13')
    f213 = fields.Char(compute="_f213")
    @api.one
    def _f214(self):
        self.f214 = self._sum_parent_id('2.14')
    f214 = fields.Char(compute="_f214")
    @api.one
    def _f215(self):
        self.f215 = self._sum_parent_id('2.15')
    f215 = fields.Char(compute="_f215")
    @api.one
    def _f216(self):
        self.f216 = self._sum_parent_id('2.16')
    f216 = fields.Char(compute="_f216")
    @api.one
    def _f217(self):
        self.f217 = self._sum_parent_id('2.17')
    f217 = fields.Char(compute="_f217")
    @api.one
    def _f218(self):
        self.f218 = self._sum_parent_id('2.18')
    f218 = fields.Char(compute="_f218")
    @api.one
    def _f219(self):
        self.f219 = self._sum_parent_id('2.19')
    f219 = fields.Char(compute="_f219")
    @api.one
    def _f220(self):
        self.f220 = self._sum_parent_id('2.20')
    f220 = fields.Char(compute="_f220")
    @api.one
    def _f221(self):
        self.f221 = self._sum_parent_id('2.21')
    f221 = fields.Char(compute="_f221")
    @api.one
    def _f222(self):
        self.f222 = self._sum_parent_id('2.22')
    f222 = fields.Char(compute="_f222")
    @api.one
    def _f223(self):
        self.f223 = self._sum_parent_id('2.23')
    f223 = fields.Char(compute="_f223")
    @api.one
    def _f224(self):
        self.f224 = self._sum_parent_id('2.24')
    f224 = fields.Char(compute="_f224")
    @api.one
    def _f225(self):
        self.f225 = self._sum_parent_id('2.25')
    f225 = fields.Char(compute="_f225")
    @api.one
    def _f226(self):
        self.f226 = self._sum_parent_id('2.26')
    f226 = fields.Char(compute="_f226")
    @api.one
    def _f227(self):
        self.f227 = self._sum_parent_id('2.27')
    f227 = fields.Char(compute="_f227")
    @api.one
    def _f228(self):
        self.f228 = self._sum_parent_id('2.28')
    f228 = fields.Char(compute="_f228")
    @api.one
    def _f229(self):
        self.f229 = self._sum_parent_id('2.29')
    f229 = fields.Char(compute="_f229")
    @api.one
    def _f230(self):
        self.f230 = self._sum_parent_id('2.30')
    f230 = fields.Char(compute="_f230")
    @api.one
    def _f231(self):
        self.f231 = self._sum_parent_id('2.31')
    f231 = fields.Char(compute="_f231")
    @api.one
    def _f232(self):
        self.f232 = self._sum_parent_id('2.32')
    f232 = fields.Char(compute="_f232")
    @api.one
    def _f233(self):
        self.f233 = self._sum_parent_id('2.33')
    f233 = fields.Char(compute="_f233")
    @api.one
    def _f234(self):
        self.f234 = self._sum_parent_id('2.34')
    f234 = fields.Char(compute="_f234")
    @api.one
    def _f235(self):
        self.f235 = self._sum_parent_id('2.35')
    f235 = fields.Char(compute="_f235")
    @api.one
    def _f236(self):
        self.f236 = self._sum_parent_id('2.36')
    f236 = fields.Char(compute="_f236")
    @api.one
    def _f237(self):
        self.f237 = self._sum_parent_id('2.37')
    f237 = fields.Char(compute="_f237")
    @api.one
    def _f238(self):
        self.f238 = self._sum_parent_id('2.38')
    f238 = fields.Char(compute="_f238")
    @api.one
    def _f239(self):
        self.f239 = self._sum_parent_id('2.39')
    f239 = fields.Char(compute="_f239")
    @api.one
    def _f240(self):
        self.f240 = self._sum_parent_id('2.40')
    f240 = fields.Char(compute="_f240")
    @api.one
    def _f241(self):
        self.f241 = self._sum_parent_id('2.41')
    f241 = fields.Char(compute="_f241")
    @api.one
    def _f242(self):
        self.f242 = self._sum_parent_id('2.42')
    f242 = fields.Char(compute="_f242")
    @api.one
    def _f243(self):
        self.f243 = self._sum_parent_id('2.43')
    f243 = fields.Char(compute="_f243")
    @api.one
    def _f244(self):
        self.f244 = self._sum_parent_id('2.44')
    f244 = fields.Char(compute="_f244")
    @api.one
    def _f245(self):
        self.f245 = self._sum_parent_id('2.45')
    f245 = fields.Char(compute="_f245")
    @api.one
    def _f246(self):
        self.f246 = self._sum_parent_id('2.46')
    f246 = fields.Char(compute="_f246")
    @api.one
    def _f247(self):
        self.f247 = self._sum_parent_id('2.47')
    f247 = fields.Char(compute="_f247")
    @api.one
    def _f248(self):
        self.f248 = self._sum_parent_id('2.48')
    f248 = fields.Char(compute="_f248")
    @api.one
    def _f249(self):
        self.f249 = self._sum_parent_id('2.49')
    f249 = fields.Char(compute="_f249")
    @api.one
    def _f250(self):
        self.f250 = self._sum_parent_id('2.50')
    f250 = fields.Char(compute="_f250")




    @api.one
    def _f301(self):
        self.f301 = self._sum_parent_id('3.1')
    f301 = fields.Char(compute="_f301")
    @api.one
    def _f302(self):
        self.f302 = self._sum_parent_id('3.2')
    f302 = fields.Char(compute="_f302")
    @api.one
    def _f303(self):
        self.f303 = self._sum_parent_id('3.3')
    f303 = fields.Char(compute="_f303")
    @api.one
    def _f304(self):
        self.f304 = self._sum_parent_id('3.4')
    f304 = fields.Char(compute="_f304")
    @api.one
    def _f305(self):
        self.f305 = self._sum_parent_id('3.5')
    f305 = fields.Char(compute="_f305")
    @api.one
    def _f306(self):
        self.f306 = self._sum_parent_id('3.6')
    f306 = fields.Char(compute="_f306")
    @api.one
    def _f307(self):
        self.f307 = self._sum_parent_id('3.7')
    f307 = fields.Char(compute="_f307")
    @api.one
    def _f308(self):
        self.f308 = self._sum_parent_id('3.8')
    f308 = fields.Char(compute="_f308")
    @api.one
    def _f309(self):
        self.f309 = self._sum_parent_id('3.9')
    f309 = fields.Char(compute="_f309")
    @api.one
    def _f310(self):
        self.f310 = self._sum_parent_id('3.10')
    f310 = fields.Char(compute="_f310")
    @api.one
    def _f311(self):
        self.f311 = self._sum_parent_id('3.11')
    f311 = fields.Char(compute="_f311")
    @api.one
    def _f312(self):
        self.f312 = self._sum_parent_id('3.12')
    f312 = fields.Char(compute="_f312")
    @api.one
    def _f313(self):
        self.f313 = self._sum_parent_id('3.13')
    f313 = fields.Char(compute="_f313")
    @api.one
    def _f314(self):
        self.f314 = self._sum_parent_id('3.14')
    f314 = fields.Char(compute="_f314")
    @api.one
    def _f315(self):
        self.f315 = self._sum_parent_id('3.15')
    f315 = fields.Char(compute="_f315")
    @api.one
    def _f316(self):
        self.f316 = self._sum_parent_id('3.16')
    f316 = fields.Char(compute="_f316")
    @api.one
    def _f317(self):
        self.f317 = self._sum_parent_id('3.17')
    f317 = fields.Char(compute="_f317")
    @api.one
    def _f318(self):
        self.f318 = self._sum_parent_id('3.18')
    f318 = fields.Char(compute="_f318")
    @api.one
    def _f319(self):
        self.f319 = self._sum_parent_id('3.19')
    f319 = fields.Char(compute="_f319")
    @api.one
    def _f320(self):
        self.f320 = self._sum_parent_id('3.20')
    f320 = fields.Char(compute="_f320")
    @api.one
    def _f321(self):
        self.f321 = self._sum_parent_id('3.21')
    f321 = fields.Char(compute="_f321")
    @api.one
    def _f322(self):
        self.f322 = self._sum_parent_id('3.22')
    f322 = fields.Char(compute="_f322")
    @api.one
    def _f323(self):
        self.f323 = self._sum_parent_id('3.23')
    f323 = fields.Char(compute="_f323")
    @api.one
    def _f324(self):
        self.f324 = self._sum_parent_id('3.24')
    f324 = fields.Char(compute="_f324")
    @api.one
    def _f325(self):
        self.f325 = self._sum_parent_id('3.25')
    f325 = fields.Char(compute="_f325")
    @api.one
    def _f326(self):
        self.f326 = self._sum_parent_id('3.26')
    f326 = fields.Char(compute="_f326")
    @api.one
    def _f327(self):
        self.f327 = self._sum_parent_id('3.27')
    f327 = fields.Char(compute="_f327")
    @api.one
    def _f328(self):
        self.f328 = self._sum_parent_id('3.28')
    f328 = fields.Char(compute="_f328")
