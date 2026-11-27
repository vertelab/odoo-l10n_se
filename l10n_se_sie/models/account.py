# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
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
        """Export moves whose date falls inside these periods.

        Ported 2026-10-30: account.move has no period_id; filter on date.
        """
        Move = self.env['account.move']
        move_ids = []
        for period in self:
            move_ids += Move.search([
                ('date', '>=', period.date_start),
                ('date', '<=', period.date_stop),
            ]).ids
        ver_ids = Move.browse(sorted(set(move_ids)))
        return self.env['account.sie'].export_sie(ver_ids)
        
#class account_chart_template(models.Model):
#    _inherit = 'account.chart.template'
#    kptyp = fields.Char(string="Kptyp")
    
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
        
    def check_missing_accounts(self,accounts):
        missing = []
        for account in accounts:
            if len(self.env['account.account'].search([('code', '=', account[0])])) == 0:
                missing.append(account)
        return missing
        
        
class account_fiscal_year(models.Model):
    _inherit = 'account.fiscal.year'

    def export_sie(self):
        """Export all moves whose date falls inside these fiscal years.

        Ported 2026-10-30 from account_period_vrtl's account.fiscalyear.
        There is no period_id on account.move any more — the period is
        derived from move.date via account.period.date2period().
        """
        Period = self.env['account.period']
        move_ids = []
        for fy in self:
            periods = Period.search([('fiscalyear_id', '=', fy.id)])
            if not periods:
                continue
            move_ids += self.env['account.move'].search([
                ('date', '>=', fy.date_from),
                ('date', '<=', fy.date_to),
            ]).ids
        ver_ids = self.env['account.move'].browse(sorted(set(move_ids)))
        return self.env['account.sie'].export_sie(ver_ids)

    def get_rar_code(self):
        """Return the RAR offset of the current date relative to this year.

        Ported 2026-10-30: date_start/date_stop -> date_from/date_to.
        """
        d = datetime.date.today()
        rar = 0
        fiscalyear = self[0]
        while True:
            if rar < -10 or rar > 10:
                break
            if fiscalyear.date_from <= d <= fiscalyear.date_to:
                break
            d -= datetime.timedelta(days=365)
            rar -= 1
        return rar


class account_journal(models.Model):
    _inherit = 'account.journal'
    serie_to_journal_ids = fields.One2many('serie.to.journal', 'journal_id', string='Series to Journal')

    # FIX FORM ON CLICK
    def send_form(self):
        if len(self > 0):
            sie_form = self[0]
  
    def export_sie(self):
        ver_ids = self.env['account.move'].search([('journal_id', 'in', self.ids)])
        _logger.warning("account journal export sie")
        return self.env['account.sie'].export_sie(ver_ids)
    
        

class serie_to_journal(models.Model):
    _name = 'serie.to.journal'
    _description = 'Serie to Journal'

    name = fields.Char(string="Serie")
    journal_id = fields.Many2one(comodel_name="account.journal", string="Journal",
                                 help="Used to set journal based on Serie of #VER", )



class account_move(models.Model):
    _inherit = 'account.move'
    
    is_incoming_balance_move = fields.Boolean(default = False)

    def export_sie(self):
        # ~ ver_ids = self.env['account.move'].search([('id','in',ids)])
        return self.env['account.sie'].export_sie(self)
        

                    
                    

