# -*- coding: utf-8 -*-
from openerp import models, fields, api, _
from openerp.exceptions import Warning

import logging
_logger = logging.getLogger(__name__)

      
class account_period(models.Model):
    _inherit = 'account.period'
    
    @api.multi
    def export_sie(self,ids):
        ver_ids = self.env['account.move'].search([('period_id','in',ids)])
        _logger.warning('\nver_ids:\n%s' % ver_ids)
        return self.env['account.sie'].make_sie2(ver_ids)
        
class account_chart_template(models.Model):
    _inherit = 'account.chart.template'
    kptyp = fields.Char(string="Kptyp")
    
class res_company(models.Model):
    _inherit = 'res.company'
    kptyp = fields.Char(string="Kptyp")
       
class account_account(models.Model):
    _inherit = 'account.account'
    
    @api.multi
    def export_sie(self,ids):
        account_ids = self.env['account.account'].browse(ids)
        ver_ids = self.env['account.move'].search([]).filtered(lambda ver: ver.line_id.filtered(lambda r: r.account_id.code in [a.code for a in account_ids]))
    
        str = self.env['account.sie'].make_sie2(ver_ids)
        _logger.warning(Response(str,headers=[
                    ('Content-Disposition', 'attachment; filename="l10n_se_sie.sie"'),
                    ('Content-Type', 'text/calendar'),
                    ('Content-Length', len(str)),
                ]))
        return Response(str, headers=[
                    ('Content-Disposition', 'attachment; filename="l10n_se_sie.sie"'),
                    ('Content-Type', 'text/calendar'),
                    ('Content-Length', len(str)),
                ])
        
        
        

class account_fiscalyear(models.Model):
    _inherit = 'account.fiscalyear'
    
    def export_sie(self,ids):
        #fiscal_year_ids = self.env['account.fiscalyear'].browse(ids)
        ver_ids = self.env['account.move'].search([]).filtered(lambda ver: ver.period_id.fiscalyear_id.id in ids)
        #_logger.warning('\n\nfiscal_year\n%s'%ver_ids)

class account_journal(models.Model):
    _inherit = 'account.journal'

    # FIX FORM ON CLICK
    def send_form(self):
        if len(self > 0):
            sie_form = self[0]
        
  
  
    def export_sie(self,ids):
#        _logger.warning('self: %s\nids: %s' %(self,ids))
        ver_ids = self.env['account.move'].search([('journal_id','in',ids)])
 #       _logger.warning('\n%s'%ver_ids)
        self.env['account.sie'].make_sie2(ver_ids)
        self.env['account_kptyp'].get_kptyp(ver_ids)
        
    
## KPTYP GREJEN två klasser. de som ska skapas. lägg på attribut
class account_kptyp(models.Model):
    _inherit = 'account.chart'
    
    @api.multi
    def get_kptyp(self,ids):
        kptyp = self.env['account.chart'].browse(ids)
        _logger.warning('\nKPTYP STUFF PARENT\n%s'%kptyp)
    
class account_kptyp_child(account_kptyp):
    
    @api.multi
    def get_kptyp(self,ids):
        _logger.warning('\nGET_KPTYP CHILD\n%s'%ids)
        super(account_kptyp_child,self).get_kptyp(ids)
