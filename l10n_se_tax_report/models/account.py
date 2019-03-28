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


# [0] när det är positiv/ja, [1] när det är negativ/nej
INK2S_MAPPING = {
    '4.1': ['7650', ''],
    '4.2': ['7750', ''],
    '4.3a': ['7651', ''],
    '4.3b': ['7652', ''],
    '4.3c': ['7653', ''],
    '4.6a': ['7654', ''],
    '4.6c': ['7655', ''],
    '4.7b': ['7656', ''],
    '4.7d': ['7657', ''],
    '4.7e': ['7658', ''],
    '4.8b': ['7659', ''],
    '4.8c': ['7660', ''],
    '4.10': ['7661', '7760'],
    '4.12': ['7662', ''],
    '4.13': ['7663', '7762'],
    '4.6e': ['7665', ''],
    '4.9': ['7666', '7765'],
    '4.6d': ['7667', ''],
    '4.6b': ['7668', ''],
    '4.15': ['7670', ''],
    '4.14b': ['7671', ''],
    '4.14c': ['7672', ''],
    '4.4a': ['7751', ''],
    '4.5a': ['7752', ''],
    '4.5b': ['7753', ''],
    '4.5c': ['7754', ''],
    '4.7a': ['7755', ''],
    '4.7c': ['7756', ''],
    '4.7f': ['7757', ''],
    '4.8a': ['7758', ''],
    '4.8d': ['7759', ''],
    '4.11': ['7761', ''],
    '4.14a': ['7763', ''],
    '4.4b': ['7764', ''],
    '4.16': ['7770', ''],
    '4.17': ['8020', ''],
    '4.18': ['8021', ''],
    '4.21': ['8022', ''],
    '4.19': ['8023', ''],
    '4.20': ['8026', ''],
    '4.22': ['8028', ''],
    u'Uppdragstagare (t.ex. redovisningskonsult) har biträtt vid upprättandet av årsredovisningen': ['8040', '8041'],
    u'Årsredovisningen har varit föremål för revision': ['8044', '8045'],
}


#~ https://www.skatteverket.se/foretagochorganisationer/arbetsgivare/lamnaarbetsgivardeklaration/hurlamnarjagarbetsgivardeklaration/saharfyllerduirutaforruta.4.3810a01c150939e893f18e43.html
class account_account(models.Model):
    _inherit = 'account.account'

    @api.multi
    def sum_period(self):
        self.ensure_one()
        return round(sum([a.balance for a in self.with_context(self._context).get_movelines()]))

    @api.multi
    def get_movelines(self):
        self.ensure_one()
        return self.env['account.move'].with_context(self._context).get_movelines().filtered(lambda l: l.account_id.id == self.id and l.move_id.journal_id.id not in l._context.get('nix_journal_ids', []))


class account_tax(models.Model):
    _inherit = 'account.tax'

    @api.one
    def _sum_period(self):
        self.sum_period = round(sum(self.get_taxlines().filtered(lambda l: l.tax_line_id.id in [self.id] + self.children_tax_ids.mapped('id')).mapped('balance')))
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
        return self.env['account.move'].with_context(self._context).get_movelines().filtered(lambda r: r.tax_line_id in self)

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
        return list(set([l.id for tax in self.tax_ids for l in tax.with_context(self._context).get_taxlines()] + [l.id for account in self.account_ids for l in account.with_context(self._context).get_movelines()]))

    @api.multi
    def get_taxlines(self):
        lines = [l.id for tax in self.tax_ids for l in tax.with_context(self._context).get_taxlines()]
        return self.env['account.move.line'].browse(lines)

    @api.onchange('sru')
    def onchange_sru(self):
        field_codes = INK2S_MAPPING.get(self.sru)
        if field_codes:
            self.field_code = field_codes[0]
            self.field_code_neg = field_codes[1]


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
