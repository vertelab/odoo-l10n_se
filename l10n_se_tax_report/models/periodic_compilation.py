# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017- Vertel AB (<http://vertel.se>).
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
from lxml import etree
import base64
from odoo.exceptions import Warning
import time
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


# order must be correct
TAGS = [
    'Supplied Goods',
    'Triangulation'
    'Services Supplied'
]

TAGS_NEW = {
    'AvdrPrelSkatt': '001', # Avdragen preliminärskatt
    'KontantErsattningUlagAG': '011', # Kontant bruttolön m.m.
    'SkatteplOvrigaFormanerUlagAG': '012', # Övriga skattepliktiga förmåner
    'SkatteplBilformanUlagAG': '013', # Skattepliktig bilförmån
    'AvdragUtgiftArbetet': '019', # Avdrag för utgifter i arbetet
    'Bilersattning': '050', # Bilersättning
    'UlagFoU': '470', # Underlag avdrag forskning och utveckling
    'AvdragFoU': '475', # Avdrag FoU
    'SummaArbAvgSlf': '487', # Summa arbetsgivaravgifter och SLF
    'SummaSkatteavdr': '497', # Summa skatteavdrag
}

class account_periodic_compilation(models.Model):
    _name = 'account.periodic.compilation'
    _inherits = {'account.declaration.line.id': 'line_id'}
    _inherit = 'account.declaration'
    # ~ _report_name = 'Periodic Compilation'
    _report_name = 'Periodisk sammanställning'
    _order = 'date desc'

    line_id = fields.Many2one('account.declaration.line.id', auto_join=True, index=True, ondelete="cascade", required=True)
    def _period_start(self):
        return  self.get_next_periods()[0]
    period_start = fields.Many2one(comodel_name='account.period', string='Start period', required=True,default=_period_start)
    # ~ period_stop = fields.Many2one(comodel_name='account.period', string='Slut period',default=_period_stop)
    invoice_ids = fields.One2many(comodel_name='account.invoice',inverse_name="periodic_compilation_id")
    line_ids = fields.One2many(comodel_name='account.declaration.line',inverse_name="periodic_compilation_id")
    move_ids = fields.One2many(comodel_name='account.move',inverse_name="periodic_compilation_id")
    
    @api.one
    def _invoice_ids_count(self):
        self.invoice_ids_count = len(self.invoice_ids)
    invoice_ids_count = fields.Integer(compute='_invoice_ids_count')


    # ~ @api.onchange('period_start')
    # ~ def _invoice_ids(self):
        # ~ slips = self.env['hr.payslip'].search([('move_id.period_id.id','=',self.period_start.id)])
        # ~ self.payslip_ids = slips.mapped('id')

        # ~ _logger.warn('jakob ***  payslip ')

        # ~ self.move_ids = []
        # ~ for move in slips.mapped('move_id'):
            # ~ move.agd_declaration_id = self.id
        # ~ _logger.info('AGD: %s %s' % (slips.mapped('id'),slips.mapped('move_id.id')))
        
    # ~ @api.multi
    # ~ def show_journal_entries(self):
        # ~ ctx = {
            # ~ 'period_start': self.period_start.id,
            # ~ 'period_stop': self.period_start.id,
            # ~ 'accounting_yearend': self.accounting_yearend,
            # ~ 'accounting_method': self.accounting_method,
            # ~ 'target_move': self.target_move,
        # ~ }
        # ~ action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_move_journal_line')
        # ~ action.update({
            # ~ 'display_name': _('Verifikat'),
            # ~ 'domain': [('id', 'in', self.move_ids.mapped('id'))],
            # ~ 'context': ctx,
        # ~ })
        # ~ return action
        
    @api.onchange('period_start')
    def onchange_period_start(self):
        if self.period_start:
            # ~ self.accounting_yearend = (self.period_start == self.fiscalyear_id.period_ids[-1] if self.fiscalyear_id else None)
            # ~ self.period_stop = self.period_start
            self.date = fields.Date.to_string(fields.Date.from_string(self.period_start.date_stop) + timedelta(days=12))
            self.name = '%s %s' % (self._report_name,self.env['account.period'].period2month(self.period_start,short=False))

    # ~ @api.onchange('period_start','target_move','accounting_method','accounting_yearend')
    @api.one
    def _vat(self):
        if self.period_start:
            ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_start.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
            self.SumSkAvdr = round(self.env.ref('l10n_se_tax_report.agd_report_SumSkAvdr').with_context(ctx).sum_tax_period()) * -1.0
            self.SumAvgBetala = round(self.env.ref('l10n_se_tax_report.agd_report_SumAvgBetala').with_context(ctx).sum_tax_period()) * -1.0
            self.ag_betala = self.SumAvgBetala + self.SumSkAvdr

    SumSkAvdr    = fields.Float(compute='_vat')
    SumAvgBetala = fields.Float(compute='_vat')
    ag_betala  = fields.Float(compute='_vat')

    @api.multi
    def show_SumSkAvdr(self):
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_start.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
        action.update({
            'display_name': _('VAT Ag'),
            'domain': [('id', 'in', self.env.ref('l10n_se_tax_report.agd_report_SumSkAvdr').with_context(ctx).get_taxlines().mapped('id'))],
            'context': {},
        })
        return action

    @api.multi
    def show_SumAvgBetala(self):
        ctx = {
                'period_start': self.period_start.id,
                'period_stop': self.period_start.id,
                'accounting_yearend': self.accounting_yearend,
                'accounting_method': self.accounting_method,
                'target_move': self.target_move,
            }
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_account_moves_all_a')
        action.update({
            'display_name': _('VAT Ag'),
            'domain': [('id', 'in', self.env.ref('l10n_se_tax_report.agd_report_SumAvgBetala').with_context(ctx).get_taxlines().mapped('id'))],
            'context': {},
        })
        return action

    @api.one
    def do_draft(self):
        for invoice in self.env['account.invoice'].search([( 'periodic_compilation_id', '=', self.id  )]):
            invoice.periodic_compilation_id = None
        self.line_ids.unlink()
        self.state='draft'
        
    @api.one
    def do_cancel(self):
        for invoice in self.invoice_ids:
            invoice.periodic_compilation_id = None

    @api.one
    def calculate(self): # make a short cut to print financial report
        if self.state not in ['draft']:
            raise Warning("Du kan inte beräkna i denna status, ändra till utkast")
        if self.state in ['draft']:
            self.state = 'confirmed'

        # ~ raise Warning ('%s  --------  %s' %  ( self.env['account.invoice'].search([('period_id.id','=',self.env['account.period'].get_period_ids(self.period_start, self.period_stop) )]), self.env['account.period'].get_period_ids(self.period_start, self.period_stop) ))
        
        partner_ids = []
        
        for invoice in self.env['account.invoice'].search([('period_id.id','=',self.env['account.period'].get_period_ids(self.period_start, self.period_stop) )]):
            
            pc_supplied_goods = sum([line.price_subtotal for line in invoice.invoice_line_ids if 'VTEU' in line.invoice_line_tax_ids.mapped('name') ])
            pc_triangulation = sum([line.price_subtotal for line in invoice.invoice_line_ids if '3FEU' in line.invoice_line_tax_ids.mapped('name') ])
            pc_services_supplied = sum([line.price_subtotal for line in invoice.invoice_line_ids if 'FTEU' in line.invoice_line_tax_ids.mapped('name') ])
            
            # ~ raise Warning( 'pc_supplied_goods = %s, pc_triangulation = %s, pc_services_supplied = %s' % (pc_supplied_goods, pc_triangulation, pc_services_supplied ) )
            # ~ _logger.warn("\n\n\n\n\n\n\n pc_supplied_goods :: %s" % pc_supplied_goods)
            # ~ _logger.warn("\n\n1111 hellooo :: %s %s" % (invoice.partner_id , self.line_ids.mapped('partner_id') ) )

            if (pc_supplied_goods + pc_triangulation + pc_services_supplied) > 0:         
                invoice.periodic_compilation_id = self.id
            
                if invoice.partner_id.id in partner_ids:
                    # ~ _logger.warn("\n\n22222 hellooo :: ")
                    line = self.line_ids.filtered( lambda l: l.partner_id == invoice.partner_id )
                    # ~ _logger.warn("\n\n22222 hellooo :: %s %s" % (line , self.line_ids ))
                    line.pc_supplied_goods += pc_supplied_goods
                    line.pc_triangulation += pc_triangulation
                    line.pc_services_supplied += pc_services_supplied
                    # ~ _logger.warn("\n\n\n\n\n\n\n line.pc_supplied_goods :: %s" % line.pc_supplied_goods)
                else:
                    self.env['account.declaration.line'].create({
                        'periodic_compilation_id': self.id,
                        'pc_supplied_goods': pc_supplied_goods,
                        'pc_triangulation': pc_triangulation,
                        'pc_services_supplied': pc_services_supplied,
                        'partner_id': invoice.partner_id.id
                    })
                    partner_ids.append(invoice.partner_id.id)

                # ~ _logger.warn("\n\n333333 hellooo :: ")
                # ~ _logger.warn("\n\n\n\n\n\n\n pc_supplied_goods :: %s" % pc_supplied_goods)

    @api.model
    def get_next_periods(self,length=1):
        last_declaration = self.search([],order='date_stop desc',limit=1)
        return self.env['account.period'].get_next_periods(last_declaration.period_start if last_declaration else None, 1)

    @api.multi
    def show_invoices(self):
        action = self.env['ir.actions.act_window'].for_xml_id('account', 'action_invoice_tree1')
        action.update({
            'display_name': _('Invoices'),
            'domain': [('periodic_compilation_id', '=', self.id )],
            'context': {},
        })
        return action

    @api.multi
    def show_invoice_lines(self):
        action = self.env['ir.actions.act_window'].for_xml_id('l10n_se_tax_report', 'action_invoice_line')
        action.update({
            'display_name': _('Invoices'),
            'domain': [('invoice_id.periodic_compilation_id', '=', self.id )],
            'context': {},
        })
        return action

class account_invoice(models.Model):
    _inherit = 'account.invoice'

    periodic_compilation_id = fields.Many2one(comodel_name="account.periodic.compilation")
    # ~ @api.one
    # ~ @api.depends('amount_total')
    # ~ def _periodic_compilation(self):
        # ~ self.pc_supplied_goods = sum([self.line_ids.filtered(lambda l: 32 in l.tax_ids.mapped('id')).mapped('total')])
        # ~ self.pc_triangulation = sum([self.line_ids.filtered(lambda l: 32 in l.tax_ids.mapped('id')).mapped('total')])
        # ~ self.pc_services_supplied = sum([self.line_ids.filtered(lambda l: 32 in l.tax_ids.mapped('id')).mapped('total')])
    # ~ pc_supplied_goods = fields.Float(string='Supplied Goods',compute='_periodic_compilation',help="Value of supplies of goods")
    # ~ pc_triangulation  = fields.Float(string='Triangulation',compute='_periodic_compilation',help="Value of a triangulation")
    # ~ pc_services_supplied  = fields.Float(string='Services Supplied',compute='_periodic_compilation',help="Value of services supplied")
    # ~ pc_purchasers_vat = fields.Char(string="VAT",relation='partner_id.vat')

class account_move(models.Model):
    _inherit = 'account.move'

    periodic_compilation_id = fields.Many2one(comodel_name="account.periodic.compilation")

class account_invoice_line(models.Model):
    _inherit = 'account.invoice.line'

    pc_vat = fields.Char(string='VAT', related='invoice_id.partner_id.vat')



class account_declaration_line(models.Model):
    _inherit = 'account.declaration.line'

    periodic_compilation_id = fields.Many2one(comodel_name="account.periodic.compilation")
    partner_id = fields.Many2one(comodel_name="res.partner")
    
    ## TRANSLATION
    # ~ pc_supplied_goods = fields.Float(string='Supplied Goods',help="Value of supplies of goods")
    # ~ pc_triangulation  = fields.Float(string='Triangulation',help="Value of a triangulation")
    # ~ pc_services_supplied  = fields.Float(string='Services Supplied',help="Value of services supplied")
    # ~ pc_purchasers_vat = fields.Char(string="VAT",relation='partner_id.vat')
    pc_supplied_goods = fields.Float(string='Levererade varor',help="Value of supplies of goods")
    pc_triangulation  = fields.Float(string='Triangulering',help="Value of a triangulation")
    pc_services_supplied  = fields.Float(string='Tillhandahållna tjänster',help="Value of services supplied")
    pc_purchasers_vat = fields.Char(string="Skatt / VAT",related='partner_id.vat')
    pc_name = fields.Char(string="Name",related='partner_id.name')

    @api.multi
    def show_invoice_lines(self):
        action = self.env['ir.actions.act_window'].for_xml_id('l10n_se_tax_report', 'action_invoice_line')
        action.update({
            'display_name': _('Verifikat'),
            'domain': [('invoice_id', 'in', self.periodic_compilation_id.invoice_ids.mapped('id')), ('partner_id', '=' ,self.partner_id.id,)],
            'context': '',
        })
        return action
        
        
