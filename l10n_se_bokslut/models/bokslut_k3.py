# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2024- Vertel Sverige AB (<http://vertel.se>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
"""K3-varderingsregler for bokslutet (BFNAR 2012:1).

K2 och K3 skiljer sig inte i hur bokforingen fors - bada foljer BFL och
BAS. De skiljer sig i VARDERING och i vilka upplysningar arsredovisningen
maste lamna. Den har modulen lagger till de tre K3-regler som faktiskt
paverkar siffrorna i bokslutet:

1. Uppskjuten skatt (BFNAR 2012:1 kap. 29)
   Temporara skillnader mellan redovisat och skattemassigt varde ska
   redovisas som uppskjuten skatteskuld (2240) eller uppskjuten
   skattefordran (1370). K2 far inte redovisa uppskjuten skatt alls -
   darfor ar den har regeln K3-only.

   Vanligaste uppkomsten: overavskrivningar (2150) och
   periodiseringsfonder (2120). Bada ar skattemassiga reserveringar som
   sanker det skattemassiga resultatet men inte det redovisade. Nar de
   loses upp reverseras den uppskjutna skatten.

2. Komponentavskrivning (BFNAR 2012:1 kap. 17.4)
   Anlaggningstillgangar med väsentligt olika nyttjandeperioder ska delas
   i komponenter som skrivs av var for sig. K2 far skriva av hela
   tillgangen pa en gemensam nyttjandeperiod.

3. Successiv vinstavrakning (BFNAR 2012:1 kap. 23)
   Pagande entreprenad- och tjansteuppdrag ska intaktsredovisas i takt
   med fardigstallandegraden nar utfallet kan beraknas tillforlitligt.
   K2 redovisar i stallet intakten nar den ar fakturerad
   (fardigstallandemetoden).

Reglerna ar raadgivande: modellen RAKNAR fram beloppen och foreslar
verifikationer, men bokfor ingenting utan att anvandaren godkanner.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

# Skattesats for svenska aktiebolag 2026 (bolagsskatt 20,6 %).
DEFAULT_TAX_RATE = 20.6


class AccountBokslutK3Mixin(models.AbstractModel):
    """Delade hjalpmetoder for K3-reglerna."""

    _name = 'account.bokslut.k3.mixin'
    _description = 'K3 Valuation Rules Helper'

    def _k3_is_active(self):
        """Returnerar True om bolaget tillampar K3."""
        self.ensure_one()
        bokslut = self.bokslut_id if 'bokslut_id' in self._fields else self
        return (bokslut.company_id.bokslut_rule_set or 'K2') == 'K3'

    def _k3_require(self):
        """Kastar fel om bolaget inte tillampar K3."""
        if not self._k3_is_active():
            raise UserError(_(
                'Den har funktionen kraver att bolaget tillampar K3. '
                'Byt regelverk under Installningar > Bokslut.'))

    def _k3_account_balance(self, code_prefixes):
        """Summan av saldot for konton med givna prefix, i bokslutsperioden."""
        self.ensure_one()
        bokslut = self.bokslut_id if 'bokslut_id' in self._fields else self
        domain = [('company_id', '=', bokslut.company_id.id)]
        accounts = self.env['account.account'].search(domain)
        accounts = accounts.filtered(
            lambda a: a.code and any(str(a.code).startswith(p)
                                     for p in code_prefixes))
        if not accounts:
            return 0.0

        period_ids = self.env['account.period'].get_period_ids(
            bokslut.period_start, bokslut.period_stop)
        total = 0.0
        for account in accounts:
            total += sum(
                period_id.with_context(
                    period_id=period_id.id,
                    target_move=bokslut.target_move,
                ).sum_period_single(account)
                for period_id in period_ids
            ) or 0.0
        return total


class AccountBokslutK3Journal(models.Model):
    """K3-falt och hjalpmetoder pa bokslutet."""
    _inherit = 'account.bokslut'

    deferred_tax_ids = fields.One2many(
        comodel_name='account.bokslut.deferred.tax',
        inverse_name='bokslut_id',
        string='Deferred Tax (K3)',
    )
    component_ids = fields.One2many(
        comodel_name='account.bokslut.component',
        inverse_name='bokslut_id',
        string='Components (K3)',
    )
    contract_progress_ids = fields.One2many(
        comodel_name='account.bokslut.contract.progress',
        inverse_name='bokslut_id',
        string='Contract Progress (K3)',
    )
    total_deferred_tax = fields.Monetary(
        string='Total Deferred Tax',
        currency_field='company_currency_id',
        compute='_compute_k3_totals',
        store=True,
    )
    total_accrued_revenue = fields.Monetary(
        string='Total Accrued Revenue',
        currency_field='company_currency_id',
        compute='_compute_k3_totals',
        store=True,
    )

    @api.depends('deferred_tax_ids.deferred_tax',
                 'contract_progress_ids.accrued_revenue')
    def _compute_k3_totals(self):
        for rec in self:
            rec.total_deferred_tax = sum(
                rec.deferred_tax_ids.mapped('deferred_tax'))
            rec.total_accrued_revenue = sum(
                rec.contract_progress_ids.mapped('accrued_revenue'))

    def _get_bokslut_journal(self):
        """Returnerar journalen som bokslutsverifikationer ska ligga i.

        Foredrar Ovr (ovriga verifikationer), faller tillbaka pa vilken
        allman journal som helst.
        """
        self.ensure_one()
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
            raise UserError(_('Ingen allman journal hittades for bolaget.'))
        return journal


class AccountBokslutDeferredTax(models.Model):
    """Uppskjuten skatt enligt BFNAR 2012:1 kap. 29.

    Temporara skillnader ar differensen mellan ett tillgangs- eller
    skuldfords redovisade varde och dess skattemassiga varde. Skillnaden
    multipliceras med skattesatsen och redovisas som uppskjuten
    skatteskuld (skattemassigt varde lagre an redovisat) eller uppskjuten
    skattefordran (det omvanda).
    """
    _name = 'account.bokslut.deferred.tax'
    _description = 'Deferred Tax (K3)'
    _order = 'sequence, id'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='Description',
        required=True,
        help='What creates the temporary difference, e.g. '
             '"Over-depreciation 2026" or "Periodization fund 2024".',
    )
    difference_type = fields.Selection(
        selection=[
            ('over_depreciation', 'Over-Depreciation (2150)'),
            ('periodization_fund', 'Periodization Fund (2120)'),
            ('other_taxable', 'Other Taxable Temporary Difference'),
            ('other_deductible', 'Other Deductible Temporary Difference'),
        ],
        string='Type',
        required=True,
        default='over_depreciation',
    )
    book_value = fields.Monetary(
        string='Book Value',
        currency_field='currency_id',
        help='The carrying amount in the accounts.',
    )
    tax_value = fields.Monetary(
        string='Tax Value',
        currency_field='currency_id',
        help='The value according to the tax return.',
    )
    temporary_difference = fields.Monetary(
        string='Temporary Difference',
        currency_field='currency_id',
        compute='_compute_temporary_difference',
        store=True,
    )
    tax_rate = fields.Float(
        string='Tax Rate (%)',
        default=DEFAULT_TAX_RATE,
        help='Swedish corporate tax rate. 20.6 % for 2026.',
    )
    deferred_tax = fields.Monetary(
        string='Deferred Tax',
        currency_field='currency_id',
        compute='_compute_deferred_tax',
        store=True,
        help='Positive = deferred tax liability (2240). '
             'Negative = deferred tax asset (1370).',
    )
    move_id = fields.Many2one(
        comodel_name='account.move',
        string='Verification',
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='bokslut_id.company_currency_id',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='bokslut_id.company_id',
    )

    @api.depends('book_value', 'tax_value')
    def _compute_temporary_difference(self):
        for rec in self:
            rec.temporary_difference = (rec.book_value or 0.0) - (rec.tax_value or 0.0)

    @api.depends('temporary_difference', 'tax_rate')
    def _compute_deferred_tax(self):
        for rec in self:
            rec.deferred_tax = (rec.temporary_difference or 0.0) * (rec.tax_rate or 0.0) / 100.0

    @api.onchange('difference_type')
    def _onchange_difference_type(self):
        """Foresla boken ur kontoplanen nar typen valjs."""
        self.ensure_one()
        bokslut = self.bokslut_id
        if not bokslut.period_start or not bokslut.period_stop:
            return
        if self.difference_type == 'over_depreciation':
            self.name = self.name or _('Over-depreciation')
            self.tax_value = 0.0
            self.book_value = self._balance_for(['2150'])
        elif self.difference_type == 'periodization_fund':
            self.name = self.name or _('Periodization fund')
            self.tax_value = 0.0
            self.book_value = self._balance_for(['2120'])

    def _balance_for(self, prefixes):
        self.ensure_one()
        bokslut = self.bokslut_id
        accounts = self.env['account.account'].search([
            ('company_id', '=', bokslut.company_id.id)])
        accounts = accounts.filtered(
            lambda a: a.code and any(str(a.code).startswith(p) for p in prefixes))
        if not accounts:
            return 0.0
        period_ids = self.env['account.period'].get_period_ids(
            bokslut.period_start, bokslut.period_stop)
        total = 0.0
        for account in accounts:
            total += sum(
                period_id.with_context(
                    period_id=period_id.id,
                    target_move=bokslut.target_move,
                ).sum_period_single(account)
                for period_id in period_ids
            ) or 0.0
        return total

    def action_create_move(self):
        """Skapa verifikation for uppskjuten skatt.

        Skuld (positiv):   Debit 8910 / Kredit 2240
        Fordran (negativ): Debit 1370 / Kredit 8910
        """
        for rec in self:
            if rec.move_id:
                continue
            if not rec.deferred_tax:
                continue
            bokslut = rec.bokslut_id
            if (bokslut.company_id.bokslut_rule_set or 'K2') != 'K3':
                raise UserError(_(
                    'Uppskjuten skatt kraver K3. Bolaget tillampar %s.',
                    bokslut.company_id.bokslut_rule_set or 'K2'))

            journal = bokslut._get_bokslut_journal()
            amount = abs(rec.deferred_tax)
            if rec.deferred_tax > 0:
                # Skatteskuld: kostnad i 8910, skuld i 2240
                lines = [
                    (rec._account('8910'), amount, 0.0),
                    (rec._account('2240'), 0.0, amount),
                ]
            else:
                # Skattefordran: tillgang i 1370, intakt i 8910
                lines = [
                    (rec._account('1370'), amount, 0.0),
                    (rec._account('8910'), 0.0, amount),
                ]

            move = self.env['account.move'].create({
                'journal_id': journal.id,
                'date': bokslut.period_stop.date_stop or fields.Date.today(),
                'ref': _('Deferred tax: %s', rec.name),
                'line_ids': [(0, 0, {
                    'account_id': account.id,
                    'name': rec.name,
                    'debit': debit,
                    'credit': credit,
                }) for account, debit, credit in lines],
            })
            rec.move_id = move
        return True

    def _account(self, code):
        self.ensure_one()
        account = self.env['account.account'].search([
            ('company_id', '=', self.bokslut_id.company_id.id),
            ('code', '=', code),
        ], limit=1)
        if not account:
            raise UserError(_(
                'Konto %s saknas i kontoplanen. Uppskjuten skatt kraver '
                'K3-kontoplanen (se_K3).', code))
        return account


class AccountBokslutComponentDepreciation(models.Model):
    """Komponentavskrivning enligt BFNAR 2012:1 kap. 17.4.

    En anlaggningstillgang vars väsentliga delar har olika
    nyttjandeperioder ska delas upp och skrivas av var for sig. Typiskt:
    en fastighet dar stommen haller 50 ar men taket 20 och
    installationerna 15.
    """
    _name = 'account.bokslut.component'
    _description = 'Component Depreciation (K3)'
    _order = 'asset_account_id, sequence, id'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(string='Component', required=True)
    asset_account_id = fields.Many2one(
        comodel_name='account.account',
        string='Asset Account',
        required=True,
        domain="[('account_type', 'in', ('asset_non_current', 'asset_fixed'))]",
    )
    acquisition_value = fields.Monetary(
        string='Acquisition Value',
        currency_field='currency_id',
        required=True,
    )
    acquisition_date = fields.Date(string='Acquisition Date')
    useful_life_years = fields.Integer(
        string='Useful Life (years)',
        required=True,
        default=5,
    )
    residual_value = fields.Monetary(
        string='Residual Value',
        currency_field='currency_id',
        help='Expected value at the end of the useful life.',
    )
    annual_depreciation = fields.Monetary(
        string='Annual Depreciation',
        currency_field='currency_id',
        compute='_compute_annual_depreciation',
        store=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='bokslut_id.company_currency_id',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='bokslut_id.company_id',
    )

    @api.depends('acquisition_value', 'residual_value', 'useful_life_years')
    def _compute_annual_depreciation(self):
        for rec in self:
            if not rec.useful_life_years:
                rec.annual_depreciation = 0.0
                continue
            base = (rec.acquisition_value or 0.0) - (rec.residual_value or 0.0)
            rec.annual_depreciation = base / rec.useful_life_years


class AccountBokslutContractProgress(models.Model):
    """Successiv vinstavrakning enligt BFNAR 2012:1 kap. 23.

    Pagande uppdrag ska intaktsredovisa i takt med fardigstallandegraden
    nar utfallet kan beraknas tillforlitligt. Upparbetad men ej fakturerad
    intakt bokfors som tillgang (1620) och fakturerad men ej upparbetad
    intakt som skuld (2450).
    """
    _name = 'account.bokslut.contract.progress'
    _description = 'Contract Progress Recognition (K3)'
    _order = 'sequence, id'

    bokslut_id = fields.Many2one(
        comodel_name='account.bokslut',
        string='Closing',
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='Project',
        required=True,
        help='Contract or project name.',
    )
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Linked Project',
    )
    contract_value = fields.Monetary(
        string='Contract Value',
        currency_field='currency_id',
        required=True,
        help='Total agreed contract revenue.',
    )
    estimated_cost = fields.Monetary(
        string='Estimated Total Cost',
        currency_field='currency_id',
        help='Expected cost to complete the whole contract.',
    )
    cost_to_date = fields.Monetary(
        string='Cost to Date',
        currency_field='currency_id',
        help='Costs incurred so far on the contract.',
    )
    completion_percentage = fields.Float(
        string='Completion (%)',
        compute='_compute_completion',
        store=True,
        help='Cost to date / estimated total cost.',
    )
    revenue_to_recognize = fields.Monetary(
        string='Revenue to Recognize',
        currency_field='currency_id',
        compute='_compute_revenue_to_recognize',
        store=True,
    )
    invoiced_amount = fields.Monetary(
        string='Invoiced',
        currency_field='currency_id',
        help='Amount already invoiced to the customer.',
    )
    accrued_revenue = fields.Monetary(
        string='Accrued Revenue',
        currency_field='currency_id',
        compute='_compute_accrued_revenue',
        store=True,
        help='Positive = work performed but not invoiced (1620). '
             'Negative = invoiced but not performed (2450).',
    )
    expected_loss = fields.Monetary(
        string='Expected Loss',
        currency_field='currency_id',
        compute='_compute_expected_loss',
        store=True,
        help='A loss-making contract must be provided for in full '
             'immediately (BFNAR 2012:1 kap. 23.31).',
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        related='bokslut_id.company_currency_id',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='bokslut_id.company_id',
    )

    @api.depends('cost_to_date', 'estimated_cost')
    def _compute_completion(self):
        for rec in self:
            if not rec.estimated_cost:
                rec.completion_percentage = 0.0
                continue
            rec.completion_percentage = min(
                100.0, (rec.cost_to_date or 0.0) / rec.estimated_cost * 100.0)

    @api.depends('contract_value', 'completion_percentage')
    def _compute_revenue_to_recognize(self):
        for rec in self:
            rec.revenue_to_recognize = (
                (rec.contract_value or 0.0) * (rec.completion_percentage or 0.0) / 100.0)

    @api.depends('revenue_to_recognize', 'invoiced_amount')
    def _compute_accrued_revenue(self):
        for rec in self:
            rec.accrued_revenue = (
                (rec.revenue_to_recognize or 0.0) - (rec.invoiced_amount or 0.0))

    @api.depends('contract_value', 'estimated_cost', 'cost_to_date')
    def _compute_expected_loss(self):
        for rec in self:
            if not rec.estimated_cost:
                rec.expected_loss = 0.0
                continue
            result = (rec.contract_value or 0.0) - rec.estimated_cost
            # Forlust avraknas i sin helhet sa fort den ar kand.
            rec.expected_loss = result if result < 0 else 0.0
