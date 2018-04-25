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


class account_tax(models.Model):
    _inherit = 'account.tax'

    sum_period = fields.Float(string='Period Sum', compute='_sum_period')

    @api.one
    def _sum_period(self):
        #~ move_state = ('posted', )
        #~ if self._context.get('state', False) == 'all':
            #~ move_state = ('draft', 'posted', )
        #~ if self._context.get('period_id', False):
            #~ period_id = self._context['period_id']
        #~ if self._context.get('period_ids', False):
            #~ move_state = ('posted', )
            #~ if self._context.get('state', False) == 'all':
                #~ move_state = ('draft', 'posted', )
            #~ period_ids = tuple(self._context['period_ids'])
        #~ else:
            #~ period_id = self.env['account.period'].find(cr, uid, context=context)
            #~ if not period_id:
                #~ return dict.fromkeys(ids, 0.0)
            #~ period_id = period_id[0]
        domain = []
        if self._context.get('period_id'):
            period = self.env['account.period'].browse(self._context.get('period_id'))
            domain += [('move_id.period_id', '=', self._context.get('period_id'))]
            #~ domain += [('date', '>=', period.date_start), ('date', '<=', period.date_stop)]
        if self._context.get('period_from') and self._context.get('period_to'):
            #~ period_from = self.env['account.period'].browse(self._context.get('period_from'))
            #~ period_to = self.env['account.period'].browse(self._context.get('period_to'))
            #~ domain += [('date', '>=', period_from.date_start), ('date', '<=', period_to.date_stop)]
            periods = self.env['account.period'].search([('date_start', '>=', self.env['account.period'].browse(self._context.get('period_from')).date_start), ('date_stop', '<=', self.env['account.period'].browse(self._context.get('period_to')).date_stop), ('special', '=', False)])
            domain += [('move_id.period_id', 'in', periods.mapped('id'))]
        if self._context.get('state'):
            if self._context.get('state') != 'all':
                domain.append(tuple(('move_id.state', '=', self._context.get('state'))))
        if self.children_tax_ids:
            def get_children_sum(tax):
                s = sum(self.env['account.move.line'].search(domain + [('tax_line_id', '=', tax.id)]).mapped('balance'))
                if tax.children_tax_ids:
                    for t in tax.children_tax_ids:
                        s += get_children_sum(t)
                return s
            self.sum_period = get_children_sum(self)
        else:
            self.sum_period = sum(self.env['account.move.line'].search(domain + [('tax_line_id', '=', self.id)]).mapped('balance'))


class account_financial_report(models.Model):
    _inherit = 'account.financial.report'

    tax_ids = fields.Many2many(comodel_name='account.tax', string='Account Tax')

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
