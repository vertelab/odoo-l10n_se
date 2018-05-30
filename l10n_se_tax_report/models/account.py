# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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

from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

#~ https://www.skatteverket.se/foretagochorganisationer/arbetsgivare/lamnaarbetsgivardeklaration/hurlamnarjagarbetsgivardeklaration/saharfyllerduirutaforruta.4.3810a01c150939e893f18e43.html
class account_account(models.Model):
    _inherit = 'account.account'
    
    @api.multi
    def sum_period(self):
        self.ensure_one()
        return sum([a.balance for a in self.get_movelines()])


    @api.multi
    def get_movelines(self):
        period_start = self._context.get('period_start',self._context.get('period_id'))
        period_stop = self._context.get('period_stop',period_start)
        # date_start / date_stop
        domain = [('period_id','in',self.env['account.period'].get_period_ids(period_start,period_stop))]
        if self._context.get('target_move') and self._context.get('target_move') in ['draft', 'posted']:
            domain.append(tuple(('state', '=', self._context.get('target_move'))))
        if self._context.get('accounting_method','invoice') == 'invoice':
            # fakturametoden
            lines = self.env['account.move'].search(domain).mapped('line_ids')
        else:
            # bokslutsmetoden / kontantmetoden
            moves = self.env['account.move'].search(domain)
            
            if self._context.get('accounting_yearend'):
                lines = moves.filtered(lambda m: any([l.full_reconcile_id for l in m.line_ids])).mapped('line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').mapped('line_ids') | moves.filtered(lambda m: all([not l.full_reconcile_id for l in m.line_ids])).mapped('line_ids')
            else:
                lines = moves.filtered(lambda m: any([l.full_reconcile_id for l in m.line_ids])).mapped('line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').mapped('line_ids') | moves.filtered(lambda m: all([not l.full_reconcile_id for l in m.line_ids]) and any([l.account_id.code[:2] == '19'])).mapped('line_ids')
        _logger.warn('Code %s --> %s (%s)'%(self.code,lines.filtered(lambda l: l.account_id in self),self))
        return lines.filtered(lambda l: l.account_id in self)


class account_tax(models.Model):
    _inherit = 'account.tax'

    @api.one
    def _sum_period(self):
        self.sum_period = sum(self.get_taxlines().filtered(lambda l: l.tax_line_id.id in [self.id] + self.children_tax_ids.mapped('id')).mapped('balance'))
    sum_period = fields.Float(string='Period Sum', compute='_sum_period')

    #~ @api.one
    #~ def _sum_period(self):
        #~ domain = []
        #~ if self._context.get('period_id'):
            #~ period = self.env['account.period'].browse(self._context.get('period_id'))
            #~ domain += [('move_id.period_id', '=', self._context.get('period_id'))]
           # domain += [('date', '>=', period.date_start), ('date', '<=', period.date_stop)]
        #~ if self._context.get('period_from') and self._context.get('period_to'):
           # period_from = self.env['account.period'].browse(self._context.get('period_from'))
           # period_to = self.env['account.period'].browse(self._context.get('period_to'))
           # domain += [('date', '>=', period_from.date_start), ('date', '<=', period_to.date_stop)]
            #~ periods = self.env['account.period'].search([('date_start', '>=', self.env['account.period'].browse(self._context.get('period_from')).date_start), ('date_stop', '<=', self.env['account.period'].browse(self._context.get('period_to')).date_stop), ('special', '=', False)])
            #~ domain += [('move_id.period_id', 'in', periods.mapped('id'))]
        #~ if self._context.get('state'):
            #~ if self._context.get('state') != 'all':
                #~ domain.append(tuple(('move_id.state', '=', self._context.get('state'))))
        #~ if self.children_tax_ids:
            #~ def get_children_sum(tax):
                #~ s = sum(self.env['account.move.line'].search(domain + [('tax_line_id', '=', tax.id)]).mapped('balance'))
                #~ if tax.children_tax_ids:
                    #~ for t in tax.children_tax_ids:
                        #~ s += get_children_sum(t)
                #~ return s
            #~ self.sum_period = get_children_sum(self)
        #~ else:
            #~ self.sum_period = sum(self.env['account.move.line'].search(domain + [('tax_line_id', '=', self.id)]).mapped('balance'))

    @api.multi  
    def get_taxlines(self):
        _logger.warn('get_taxlines context %s' % self._context)
        _logger.warn('get_taxlines self %s' % self)
        period_start = self._context.get('period_start',self._context.get('period_id'))
        period_stop = self._context.get('period_stop',period_start)
        # date_start / date_stop
        domain = [('period_id','in',self.env['account.period'].get_period_ids(period_start,period_stop))]
        if self._context.get('target_move') and self._context.get('target_move') in ['draft', 'posted']:
            domain.append(tuple(('state', '=', self._context.get('target_move'))))
        if self._context.get('accounting_method','invoice') == 'invoice':
            # fakturametoden
            lines = self.env['account.move'].search(domain).mapped('line_ids')
        else:
            # bokslutsmetoden / kontantmetoden
            moves = self.env['account.move'].search(domain)
            if self._context.get('accounting_yearend'):
                lines = moves.filtered(lambda m: any([l.full_reconcile_id for l in m.line_ids])).mapped('line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').mapped('line_ids') | moves.filtered(lambda m: all([not l.full_reconcile_id for l in m.line_ids])).mapped('line_ids')
            else:
                lines = moves.filtered(lambda m: any([l.full_reconcile_id for l in m.line_ids])).mapped('line_ids').mapped('full_reconcile_id').mapped('reconciled_line_ids').mapped('move_id').mapped('line_ids') | moves.filtered(lambda m: all([not l.full_reconcile_id for l in m.line_ids]) and any([l.account_id.code[:2] == '19'])).mapped('line_ids')
            
            #~ lines = self.env['account.move'].search(domain)
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('line_ids')
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('full_reconcile_id')
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('reconciled_line_ids')
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('move_id')
            #~ _logger.warn(lines)
            #~ lines = lines.mapped('line_ids')
        

        return lines.filtered(lambda r: r.tax_line_id in self)

    @api.model  
    def get_taxtable(self):
        tax = {tax.code:line.balance for line in self.get_taxlines() for tax in line.mapped('tax_ids')}
        return tax
        
    
        
class account_financial_report(models.Model):
    _inherit = 'account.financial.report'

    sru = fields.Char(string='SRU Code')
    field_code = fields.Char(string='Field Code', help="Code for Swedish electronic reporting. If Field code (Negative) has a value, Field code is only used for positive results.")
    field_code_neg = fields.Char(string='Field Code (Negative)', help="Code for Swedish electronic reporting. Only used if result is negative. If this field has a value, Field code is only used for positive results.")
    tax_ids = fields.Many2many(comodel_name='account.tax', string='Account Tax')

    @api.multi
    def sum_tax_period(self):
        _logger.warn('sum_tax_period context %s' %self._context )
        return sum([t.with_context(self._context).sum_period for t in self.tax_ids])

    @api.multi
    def get_moveline_ids(self):
        _logger.warn('financial report %s',self)
        for account in self.account_ids:
            _logger.warn('account: %s --> %s (%s)' % (account.code,account.with_context(self._context).get_movelines(),self._context))
            _logger.warn('account: %s >>> %s' % (account.code,[l.id for account in self.account_ids for l in account.with_context(self._context).get_movelines()]))

        for tax in self.tax_ids:
            _logger.warn('tax: %s' % tax.name)
            _logger.warn(tax.with_context(self._context).get_taxlines())
        return list(set([l.id for tax in self.tax_ids for l in tax.with_context(self._context).get_taxlines()] + [l.id for account in self.account_ids for l in account.with_context(self._context).get_movelines()]))
        
    @api.multi
    def get_taxlines(self):
        _logger.warn(self.name)
        _logger.warn(self._context)
        for tax in self.tax_ids:
            _logger.warn('tax: %s' % tax.name)
            _logger.warn(tax.with_context(self._context).get_taxlines())
        lines = [l.id for tax in self.tax_ids for l in tax.with_context(self._context).get_taxlines()]
        return self.env['account.move.line'].browse(lines)

    @api.model
    def create(self, vals):
        res = super(account_financial_report, self).create(vals)
        res.account_ids |= res.tax_ids.mapped('children_tax_ids').mapped('account_id') | res.tax_ids.mapped('account_id')
        return res

    @api.multi
    def write(self, vals):
        res = super(account_financial_report, self).write(vals)
        if 'tax_ids' in vals:
            self.account_ids |= self.tax_ids.mapped('children_tax_ids').mapped('account_id') | self.tax_ids.mapped('account_id')
        return res


class ReportFinancial(models.AbstractModel):
    _inherit = 'report.account.report_financial'

    def _compute_report_balance(self, reports):
        res = super(ReportFinancial, self)._compute_report_balance(reports)
        if res.keys()[0] == self.env.ref('l10n_se_tax_report.root').id: # make sure the first line is momsrapport
            ctx = {
                'period_from': self.env['account.period'].date2period(self._context.get('date_from')).id,
                'period_to': self.env['account.period'].date2period(self._context.get('date_to')).id
            }
            for i in res.keys()[1:]:
                afr = self.env['account.financial.report'].browse(i)
                if afr and afr.type == 'accounts' and len(afr.tax_ids) > 0:
                    if afr == self.env.ref('l10n_se_tax_report.49'):
                        res[i]['balance'] = int(round(-(self.env['account.tax'].search([('name', '=', 'MomsUtg')]).with_context(ctx).sum_period + self.env['account.tax'].search([('name', '=', 'MomsIngAvdr')]).with_context(ctx).sum_period)))
                    elif len(afr.tax_ids) > 0:
                        res[i]['balance'] = int(round(abs(afr.with_context(ctx).sum_tax_period())))
        if res.keys()[0] == self.env.ref('l10n_se_tax_report.agd_report').id: # make sure the first line is agdrapport
            ctx = {
                'period_from': self.env['account.period'].date2period(self._context.get('date_from')).id,
                'period_to': self.env['account.period'].date2period(self._context.get('date_to')).id
            }
            for i in res.keys()[1:]:
                afr = self.env['account.financial.report'].browse(i)
                if afr and afr.type == 'accounts' and len(afr.tax_ids) > 0:
                    res[i]['balance'] = int(round(abs(afr.with_context(ctx).sum_tax_period())))
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
