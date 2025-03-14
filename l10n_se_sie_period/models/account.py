# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import datetime

import logging
_logger = logging.getLogger(__name__)


class account_period(models.Model):
    _inherit = 'account.period'
    
    def export_sie(self):
        ver_ids = self.env['account.move'].search([('period_id','in',self.ids)])
        return self.env['account.sie'].export_sie(ver_ids)
        
class account_fiscalyear(models.Model):
    _inherit = 'account.fiscalyear'
    
    def export_sie(self):
        #fiscal_year_ids = self.env['account.fiscalyear'].browse(ids)
        ver_ids = self.env['account.move'].search([]).filtered(lambda ver: ver.period_id.fiscalyear_id.id in self.ids)
        #_logger.warning('\n\nfiscal_year\n%s'%ver_ids)
        return self.env['account.sie'].export_sie(ver_ids)

    def get_rar_code(self):
        d = datetime.date.today()
        rar = 0
        fiscalyear = self[0]
        while True:            
            if rar < -10 or rar > 10:
                break
            if d.strftime('%Y-%m-%s') >= fiscalyear.date_start and d.strftime('%Y-%m-%s') <= fiscalyear.date_stop:
                break
            
            d -= datetime.timedelta(days=365)
            rar -= 1
        return rar


                    
                    

