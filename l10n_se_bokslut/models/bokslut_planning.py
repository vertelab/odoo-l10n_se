# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel AB (<http://vertel.se>).
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
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountBokslut(models.Model):
    _name = 'account.bokslut'
    _inherit = ['account.declaration']
    _description = 'Year-End Closing'

    fiscalyear_id = fields.Many2one(
        comodel_name='account.fiscalyear',
        string='Fiscal Year',
        required=True,
    )
    period_start = fields.Many2one(
        comodel_name='account.period',
        string='Start Period',
    )
    period_stop = fields.Many2one(
        comodel_name='account.period',
        string='End Period',
    )
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Closing Project',
        help='Linked project containing the checklist (Kanban tasks) and milestones.',
    )
    report_id = fields.Many2one(
        comodel_name='account.financial.report',
        string='Financial Report Structure',
        help='The account.financial.report structure used for BR/RR.',
    )
    adjustment_ids = fields.One2many(
        comodel_name='account.bokslut.adjustment',
        inverse_name='bokslut_id',
        string='Adjustments',
    )
    tax_calculation_ids = fields.One2many(
        comodel_name='account.bokslut.tax.calc',
        inverse_name='bokslut_id',
        string='Tax Calculation',
    )
    periodization_fund_ids = fields.One2many(
        comodel_name='account.periodization.fund',
        inverse_name='bokslut_id',
        string='Periodization Funds',
    )
    excess_depreciation_ids = fields.One2many(
        comodel_name='account.excess.depreciation',
        inverse_name='bokslut_id',
        string='Excess Depreciation',
    )
    schablonintakt = fields.Monetary(
        string='Schablonintäkt',
        currency_field='company_currency_id',
        compute='_compute_schablonintakt',
        store=True,
        help='Schablonintäkt på periodiseringsfonder (statslåneränta × summa fonder).',
    )
    # Computed results
    resultat_fore_bokslut = fields.Monetary(
        string='Result Before Dispositions',
        currency_field='company_currency_id',
        readonly=True,
    )
    resultat_fore_skatt = fields.Monetary(
        string='Result Before Tax',
        currency_field='company_currency_id',
        readonly=True,
    )
    arets_skattekostnad = fields.Monetary(
        string='Tax Cost',
        currency_field='company_currency_id',
        readonly=True,
    )
    arets_resultat = fields.Monetary(
        string='Net Result',
        currency_field='company_currency_id',
        readonly=True,
    )
    annual_report_id = fields.Many2one(
        comodel_name='account.annual.report',
        string='Annual Report',
        readonly=True,
    )
    company_currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='company_id.currency_id',
    )

    @api.onchange('fiscalyear_id')
    def _onchange_fiscalyear_id(self):
        """Set period_start/period_stop from fiscal year."""
        if self.fiscalyear_id:
            periods = self.env['account.period'].search([
                ('fiscalyear_id', '=', self.fiscalyear_id.id),
                ('special', '=', False),
            ], order='date_start asc')
            if periods:
                self.period_start = periods[0]
                self.period_stop = periods[-1]
            self.name = _('Bokslut %s') % self.fiscalyear_id.name

    def action_create_checklist_project(self):
        """Create a project.project with checklist tasks and milestones."""
        self.ensure_one()
        if self.project_id:
            return self.action_open_checklist()

        # Create project
        project = self.env['project.project'].create({
            'name': _('Bokslut %s — %s') % (self.fiscalyear_id.name, self.company_id.name),
            'company_id': self.company_id.id,
            'allow_milestones': True,
        })
        self.project_id = project.id

        # Copy checklist task templates
        templates = self.env['project.task'].search([
            ('is_template', '=', True),
            ('bokslut_section', '!=', False),
        ], order='sequence')
        default_stage = self.env.ref('l10n_se_bokslut.bokslut_stage_todo', raise_if_not_found=False)
        for template in templates:
            template.copy({
                'project_id': project.id,
                'is_template': False,
                'stage_id': default_stage.id if default_stage else False,
            })

        # Create milestones
        if self.period_stop and self.period_stop.date_stop:
            year_end = fields.Date.from_string(self.period_stop.date_stop)
            milestones = [
                (_('Bank Reconciliation Done'), year_end.replace(month=year_end.month + 1, day=15) if year_end.month < 12 else fields.Date.to_date('%s-01-15' % (year_end.year + 1))),
                (_('VAT Q4 Submitted'), None),  # TODO: calculate from deadline
                (_('SRU Generated'), fields.Date.to_date('%s-07-01' % (year_end.year + 1))),
                (_('Annual Report Signed'), fields.Date.to_date('%s-07-31' % (year_end.year + 1))),
                (_('Submitted to Bolagsverket'), fields.Date.to_date('%s-08-31' % (year_end.year + 1))),
            ]
            for name, deadline in milestones:
                milestone_vals = {
                    'name': name,
                    'project_id': project.id,
                }
                if deadline:
                    milestone_vals['deadline'] = deadline
                self.env['project.milestone'].create(milestone_vals)

        # Add activities for deadlines
        self.env['mail.activity'].create({
            'res_model_id': self.env['ir.model']._get_id('account.bokslut'),
            'res_id': self.id,
            'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
            'summary': _('Year-end closing deadline: %s') % self.fiscalyear_id.name,
            'date_deadline': self.period_stop.date_stop if self.period_stop else fields.Date.today(),
            'user_id': self.env.uid,
        })

        return self.action_open_checklist()

    def action_open_checklist(self):
        """Open the project's Kanban view."""
        self.ensure_one()
        if not self.project_id:
            return self.action_create_checklist_project()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bokslut Checklista'),
            'res_model': 'project.task',
            'view_mode': 'kanban,tree,form,calendar',
            'domain': [('project_id', '=', self.project_id.id)],
            'context': {
                'default_project_id': self.project_id.id,
                'search_default_group_by_stage': 1,
            },
        }

    @api.depends('periodization_fund_ids', 'periodization_fund_ids.remaining')
    def _compute_schablonintakt(self):
        for rec in self:
            rec.schablonintakt = self.env['account.periodization.fund'].calculate_schablonintakt(rec)

    def calculate_resultat(self):
        """Calculate result before dispositions (accounts 3000-8999)."""
        self.ensure_one()
        if not self.period_start or not self.period_stop:
            raise UserError(_('Start and end periods must be set.'))

        # Get all accounts in range 3000-8999
        accounts = self.env['account.account'].search([
            ('code', '>=', '3000'),
            ('code', '<=', '8999'),
            ('company_id', '=', self.company_id.id),
        ])
        if not accounts:
            return

        # Get period IDs
        period_ids = self.env['account.period'].get_period_ids(
            self.period_start, self.period_stop
        )

        # Sum balances
        total_balance = 0.0
        for account in accounts:
            balance = sum(
                period_id.with_context(
                    period_id=period_id.id,
                    target_move=self.target_move,
                ).sum_period_single(account)
                for period_id in period_ids
            )
            total_balance += balance or 0.0

        self.resultat_fore_bokslut = total_balance
        return total_balance

    def calculate_skatt(self):
        """Full tax calculation chain including periodization funds and excess depreciation."""
        self.ensure_one()

        # Ensure result is calculated
        if not self.resultat_fore_bokslut and not self._context.get('skip_calc'):
            self.calculate_resultat()

        result = self.resultat_fore_bokslut or 0.0

        # Sum adjustments
        non_deductible = sum(
            adj.amount for adj in self.adjustment_ids
            if adj.type == 'non_deductible' and adj.amount
        )
        non_taxable = sum(
            adj.amount for adj in self.adjustment_ids
            if adj.type == 'non_taxable' and adj.amount
        )
        deductible = sum(
            adj.amount for adj in self.adjustment_ids
            if adj.type == 'cost' and adj.amount
        )
        taxable_income = sum(
            adj.amount for adj in self.adjustment_ids
            if adj.type == 'income' and adj.amount
        )

        # Periodization funds
        period_reversal = sum(
            f.reversal_amount for f in self.periodization_fund_ids if f.reversal_amount
        )
        period_allocation = sum(
            f.amount for f in self.periodization_fund_ids
            if f.state == 'active' and f.reversal_amount == 0
        )
        # Schablonintäkt
        self._compute_schablonintakt()
        schablon = self.schablonintakt or 0.0

        # Excess depreciation
        total_excess = sum(
            d.excess_depreciation for d in self.excess_depreciation_ids
            if d.excess_depreciation
        )

        # Taxable result
        taxable_result = (
            result
            + non_deductible
            - non_taxable
            + deductible
            - taxable_income
            + schablon
            + period_reversal
            - period_allocation
            - total_excess
        )

        # Swedish corporate tax rate: 20.6%
        tax_rate = 0.206
        skatt = taxable_result * tax_rate if taxable_result > 0 else 0.0

        self.resultat_fore_skatt = taxable_result
        self.arets_skattekostnad = skatt
        self.arets_resultat = result - skatt

        # Build/update tax calculation lines for display
        self.tax_calculation_ids.unlink()
        lines = [
            (1, _('Result Before Dispositions'), result),
            (2, _('+ Non-Deductible Costs'), non_deductible),
            (3, _('- Non-Taxable Income'), -non_taxable),
            (4, _('+/- Other Adjustments'), deductible - taxable_income),
            (5, _('+ Schablonintäkt (Periodization Funds)'), schablon),
            (6, _('+ Periodization Fund Reversal'), period_reversal),
            (7, _('- Periodization Fund Allocation'), -period_allocation),
            (8, _('- Excess Depreciation'), -total_excess),
            (9, _('= Taxable Result'), taxable_result),
            (10, _('Tax (20.6%)'), skatt),
            (11, _('= Net Result'), self.arets_resultat),
        ]
        for seq, name, amount in lines:
            self.env['account.bokslut.tax.calc'].create({
                'bokslut_id': self.id,
                'sequence': seq,
                'name': name,
                'amount': amount,
            })

    def generate_verifications(self):
        """Generate closing verifications (8999 <-> 2099)."""
        self.ensure_one()
        if not self.arets_resultat:
            self.calculate_skatt()

        journal = self.env['account.journal'].search([
            ('code', '=', 'Ovr'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal:
            journal = self.env['account.journal'].search([
                ('type', '=', 'general'),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
        if not journal:
            raise UserError(_('No general journal found.'))

        period = self.period_stop
        if not period:
            raise UserError(_('End period must be set.'))

        entry = self.move_id
        if not entry:
            entry = self.env['account.move'].create({
                'journal_id': journal.id,
                'date': period.date_stop,
                'ref': _('Bokslut %s') % self.fiscalyear_id.name,
                'move_type': 'entry',
            })
            self.move_id = entry.id

        # Find accounts
        konto_8999 = self.env['account.account'].search([
            ('code', '=', '8999'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        konto_2099 = self.env['account.account'].search([
            ('code', '=', '2099'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)

        if not konto_8999 or not konto_2099:
            raise UserError(_('Accounts 8999 and 2099 must exist.'))

        resultat = abs(self.arets_resultat)
        is_profit = self.arets_resultat >= 0

        # Clear existing lines
        entry.line_ids.unlink()

        # Profit: 8999 (D) / 2099 (K)
        # Loss:   2099 (D) / 8999 (K)
        lines = [
            (0, 0, {
                'name': konto_8999.name,
                'account_id': konto_8999.id,
                'debit': resultat if is_profit else 0.0,
                'credit': 0.0 if is_profit else resultat,
                'move_id': entry.id,
            }),
            (0, 0, {
                'name': konto_2099.name,
                'account_id': konto_2099.id,
                'debit': 0.0 if is_profit else resultat,
                'credit': resultat if is_profit else 0.0,
                'move_id': entry.id,
            }),
        ]
        entry.write({'line_ids': lines})

    def action_book_preliminary(self):
        """Post verifications as preliminary (affects account.bokslut balance only)."""
        self.ensure_one()
        self.generate_verifications()
        if self.move_id:
            # Preliminary booking: keep as draft but mark bokslut state
            self.state = 'confirmed'
            # Tag the move with bokslut context
            self.move_id.write({'ref': _('Bokslut (Preliminary) %s') % self.fiscalyear_id.name})

    def action_book(self):
        """Final booking of all verifications."""
        self.ensure_one()
        self.generate_verifications()
        if self.move_id and self.move_id.state == 'draft':
            self.move_id.action_post()
        # Also post any adjustment moves
        for adj in self.adjustment_ids:
            if adj.move_id and adj.move_id.state == 'draft':
                adj.move_id.action_post()
        self.state = 'done'

    def action_generate_annual_report(self):
        """Generate the annual report from this closing."""
        self.ensure_one()
        if not self.annual_report_id:
            report = self.env['account.annual.report'].create({
                'bokslut_id': self.id,
                'fiscalyear_id': self.fiscalyear_id.id,
                'company_id': self.company_id.id,
                'rule_set': self.company_id.bokslut_rule_set or 'K2',
            })
            self.annual_report_id = report.id
        self.annual_report_id.generate()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Annual Report'),
            'res_model': 'account.annual.report',
            'res_id': self.annual_report_id.id,
            'view_mode': 'form',
        }


class AccountBokslutTaxCalc(models.Model):
    _name = 'account.bokslut.tax.calc'
    _description = 'Tax Calculation Line'
    _order = 'sequence'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(string='Order', default=10)
    name = fields.Char(string='Description', required=True)
    amount = fields.Monetary(string='Amount', currency_field='currency_id')
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='bokslut_id.company_currency_id',
    )
