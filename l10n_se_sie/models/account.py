# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning
import datetime

import logging
_logger = logging.getLogger(__name__)


# class wizard_multi_charts_accounts(models.TransientModel):
#     _inherit = 'wizard.multi.charts.accounts'
#
#     def execute(self):
#         config = self[0]
#         res = super(wizard_multi_charts_accounts, self).execute()
#         if config.chart_template_id:
#             config.company_id.kptyp = config.chart_template_id.kptyp
#         return res

class account_period(models.Model):
    _inherit = 'account.period'
    
    def export_sie(self):
        ver_ids = self.env['account.move'].search([('period_id','in',self.ids)])
        return self.env['account.sie'].export_sie(ver_ids)
        
class account_chart_template(models.Model):
    _inherit = 'account.chart.template'
    kptyp = fields.Char(string="Kptyp")
    
class res_company(models.Model):
    _inherit = 'res.company'
    kptyp = fields.Char(string="Kptyp")
       
class account_account(models.Model):
    _inherit = 'account.account'
    
    def export_sie(self):
        # ~ account_ids = self.env['account.account'].browse(self.ids)
        ver_ids = self.env['account.move'].search([]).filtered(lambda ver: ver.line_ids.filtered(lambda r: r.account_id.code in [a.code for a in self]))
        _logger.warning(f"export_sie {ver_ids}")
        return self.env['account.sie'].export_sie(ver_ids)
        
    def check__missing_accounts(self,accounts):
        missing = []
        for account in accounts:
            if len(self.env['account.account'].search([('code', '=', account[0])])) == 0:
                missing.append(account)
        return missing
        
        
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


class account_journal(models.Model):
    _inherit = 'account.journal'

    # FIX FORM ON CLICK
    def send_form(self):
        if len(self > 0):
            sie_form = self[0]
  
    def export_sie(self):
        ver_ids = self.env['account.move'].search([('journal_id', 'in', self.ids)])
        return self.env['account.sie'].export_sie(ver_ids)


class account_move(models.Model):
    _inherit = 'account.move'

    def export_sie(self):
        # ~ ver_ids = self.env['account.move'].search([('id','in',ids)])
        return self.env['account.sie'].export_sie(self)
