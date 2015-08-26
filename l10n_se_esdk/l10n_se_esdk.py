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
from openerp import http
from openerp.http import request
from openerp import SUPERUSER_ID
from datetime import datetime
import werkzeug
import pytz
import re

import logging
_logger = logging.getLogger(__name__)

class account_tax_esdk(models.Model):
    """
        <UttagMoms>200000</UttagMoms>
        <UlagMargbesk>300000</UlagMargbesk>
        <HyrinkomstFriv>400000</HyrinkomstFriv>
        <InkopVaruAnnatEg>5000</InkopVaruAnnatEg>
        <InkopTjanstAnnatEg>6000</InkopTjanstAnnatEg>
        <InkopTjanstUtomEg>7000</InkopTjanstUtomEg>
        <InkopVaruSverige>8000</InkopVaruSverige>
        <InkopTjanstSverige>9000</InkopTjanstSverige>
        <MomsUlagImport>10000</MomsUlagImport>
        <ForsVaruAnnatEg>11000</ForsVaruAnnatEg>
        <ForsVaruUtomEg>12000</ForsVaruUtomEg>
        <InkopVaruMellan3p>13000</InkopVaruMellan3p>
        <ForsVaruMellan3p>14000</ForsVaruMellan3p>
        <ForsTjSkskAnnatEg>15000</ForsTjSkskAnnatEg>
        <ForsTjOvrUtomEg>16000</ForsTjOvrUtomEg>
        <ForsKopareSkskSverige>17000</ForsKopareSkskSverige>
        <ForsOvrigt>18000</ForsOvrigt>
        <MomsUtgHog>200000</MomsUtgHog>
        <MomsUtgMedel>15000</MomsUtgMedel>
        <MomsUtgLag>5000</MomsUtgLag>
        <MomsInkopUtgHog>2500</MomsInkopUtgHog>
        <MomsInkopUtgMedel>1000</MomsInkopUtgMedel>
        <MomsInkopUtgLag>500</MomsInkopUtgLag>
        <MomsImportUtgHog>2000</MomsImportUtgHog>
        <MomsImportUtgMedel>350</MomsImportUtgMedel>
        <MomsImportUtgLag>150</MomsImportUtgLag>
        <MomsIngAvdr>1000</MomsIngAvdr>
        <MomsBetala>225500</MomsBetala>
        <TextUpplysningMoms>Bla bla bla bla</TextUpplysningMoms>
      </Moms>
      
      
      https://support.speedledger.se/hc/sv/articles/204207739-Momskoder
      
      
    """

    _name = 'account.tax.esdk'
    _description = 'Tax reporting'
    _order = 'name'



    name = fields.Char('Tax Period',required=True)
    company_id = fields.Many2one('res.company', string='Company', change_default=True,
        required=True, readonly=True, states={'draft': [('readonly', False)]},
        default=lambda self: self.env['res.company']._company_default_get('account.tax.esdk'))
    state = fields.Selection([('draft','Open'), ('done','Closed')], 'Status', default='draft',readonly=False, copy=False)
    date_start = fields.Date('Date start')
    date_stop = fields.Date('Date stop')
    period_id = fields.Many2one('account.period', string='Force Period',
        domain=[('state', '!=', 'done')], copy=False,
        help="Keep empty to use the period of the validation(invoice) date.",
        readonly=True, states={'draft': [('readonly', False)]})
    description = fields.Text('Note')

 

    @api.multi
    def get_tax_sum(self,code):
        return 30
        #return self.env['account.tax.code'].search[('code','=',code)][0].sum  

    @api.one
    def create_period(self,):
        
        return self.env['account.tax.code'].search[('code','=',code)][0].sum  



#----------------------------------------------------------
# Tax
#----------------------------------------------------------

class account_tax_code(models.Model):
    _inherit = 'account.tax.code'

    
    def _sum_periods(self,context):
        move_state = ('posted', )
        if context.get('state', False) == 'all':
            move_state = ('draft', 'posted', )
        if context.get('period_ids', False):
            period_ids = context['period_ids']
        else:
            period_ids = self.env['account.period'].find()
        return self._sum(self.cr, self.uid, [], '', [], context,
                where=' AND line.period_id IN %s AND move.state IN %s', where_params=(period_ids, move_state))


    sum_periods = fields.Float('Periods Sum',compute='_sum_periods')
    
    

