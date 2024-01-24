# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2017 Vertel (<http://vertel.se>).
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

import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter

# from openerp.osv import osv

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError, ValidationError

import base64
from odoo.tools.safe_eval import safe_eval as eval

try:
    from xlrd import open_workbook
except ImportError:
    raise Warning('excel library missing, pip install xlrd')

import logging

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    type = fields.Selection(selection_add=[('bg', 'Bankgiro'), ('pg', 'Plusgiro')],
                            ondelete={'bg': 'cascade', 'pg': 'cascade'})


class AccountChartTemplate(models.Model):
    _inherit = 'account.account'

    @api.model
    def fix_ovriga_kortfristiga_skulder(self):
        # Fix  account.data_account_type_current_liabilities, set type to payable and all accounts 8/25 detta är ändrat till payable så att vi kan snappa upp löne spec verfikat när vi gör en payment order. Kanske förstör något annat i odoo.
        OvrigaKortfristigaSkulder = self.env.ref('account.data_account_type_current_liabilities')
        for acc in self.env['account.account'].search([('user_type_id', '=', OvrigaKortfristigaSkulder.id)]):
            acc.reconcile = True
        OvrigaKortfristigaSkulder.type = 'payable'

    @api.model
    def fix_type_personalkostnader(self):
        # Fix  l10n_se.type_Personalkostnader, detta är gjort så att vi kan använda oss av 7331(Skattefria bilersättningar ) som skuld kont när vi har en millersättning utlägg
        type_personalkostnader = self.env.ref('l10n_se.type_Personalkostnader')
        for acc in self.env['account.account'].search([('user_type_id', '=', type_personalkostnader.id)]):
            acc.reconcile = True
        type_personalkostnader.type = 'payable'

    @api.model
    def fix_account_types(self):
        # current_year_earnings can only have one account which is why we remove it before we fix the rest of the account types.
        current_year_earnings = self.env.ref('account.data_unaffected_earnings')
        current_year_earnings.write({"name": 'Current Year Earnings'})
        current_year_earnings.write({"account_range": "[('code', 'in', [])]"})
        current_year_earnings.write({"account_range": False})

        for t in self.env['account.account.type'].search([]):
            if t.account_range:
                for a in self.env['account.account'].search(eval(t.account_range)):
                    if a.user_type_id != t:
                        a.user_type_id = t

        # Hard coded/Not based on the excel sheet that
        accounts = self.env['account.account'].search(['|', ('code', '=', '1330'), ('code', '=', '1338')])
        for account in accounts:
            account.user_type_id = self.env.ref('l10n_se.type_AndelarIntresseforetagGemensamtStyrdaForetag')

        accounts = self.env['account.account'].search(['|', ('code', '=', '1340'), ('code', '=', '1348')])
        for account in accounts:
            account.user_type_id = self.env.ref(
                'l10n_se.type_FordringarIntresseforetagGemensamtStyrdaForetagLangfristiga')

        accounts = self.env['account.account'].search(['|', ('code', '=', '1570'), ('code', '=', '1670')])
        for account in accounts:
            account.user_type_id = self.env.ref(
                'l10n_se.type_FordringarIntresseforetagGemensamtStyrdaForetagKortfristiga')

        # ~ accounts = self.env['account.account'].search(['|','|',('code', '=', '2087'),('code', '=', '2088'),('code', '=', '2089')])
        # ~ for account in accounts:
        # ~ account.user_type_id = self.env.ref('l10n_se.type_FordringarIntresseforetagGemensamtStyrdaForetagKortfristiga')
        accounts = self.env['account.account'].search([('code', '=', '2090')])
        for account in accounts:
            account.user_type_id = self.env.ref('l10n_se.type_BalanseratResultat')

        accounts = self.env['account.account'].search([('code', '=', '2370')])
        for account in accounts:
            account.user_type_id = self.env.ref('l10n_se.type_SkulderIntresseforetagGemensamtStyrdaForetagLangfristiga')

        accounts = self.env['account.account'].search(['|', ('code', '=', '2470'), ('code', '=', '2870')])
        for account in accounts:
            account.user_type_id = self.env.ref('l10n_se.type_SkulderIntresseforetagGemensamtStyrdaForetagKortfristiga')

        accounts = self.env['account.account'].search([('code', '=', '2490')])
        for account in accounts:
            account.user_type_id = self.env.ref('account.data_account_type_current_liabilities')

        # ~ accounts = self.env['account.account'].search([('code', '>=', '2900'),('code', '<=', '2999')])
        # ~ for account in accounts:
        # ~ account.user_type_id = self.env.ref('l10n_se.type_ForutbetaldaKostnaderUpplupnaIntakter')

        accounts = self.env['account.account'].search([('code', '=', '4900')])
        for account in accounts:
            account.user_type_id = self.env.ref(
                'l10n_se.type_ForandringLagerProdukterIArbeteFardigaVarorPagaendeArbetenAnnansRakning')

        accounts = self.env['account.account'].search(
            ['|', '|', '|', '|', ('code', '=', '8110'), ('code', '=', '8116'), ('code', '=', '8117'),
             ('code', '=', '8120'), ('code', '=', '8130')])
        for account in accounts:
            account.user_type_id = self.env.ref('l10n_se.type_ResultatAndelarIntresseforetagGemensamtStyrda')

        accounts = self.env['account.account'].search([('code', '=', '8118')])
        for account in accounts:
            account.user_type_id = self.env.ref('l10n_se.type_ResultatOvrigaforetagAgarintresse')

        accounts = self.env['account.account'].search([('code', '=', '8840')])
        for account in accounts:
            account.user_type_id = self.env.ref('l10n_se.type_OvrigaBokslutsdispositioner')

        # Setting the correct type for the moms accounts since they need to belong to a account type that is of the type "regular", otherwise they don't behave correctly when making invoices.
        accounts = self.env['account.account'].search([('code', 'in',
                                                        ['2610', '2611', '2612', '2613', '2614', '2615', '2616', '2618',
                                                         '2620', '2621', '2622', '2623', '2624', '2625', '2626', '2628',
                                                         '2630', '2631', '2632', '2633', '2634', '2635', '2636', '2638',
                                                         '2640', '2641', '2642', '2645', '2646', '2647', '2648', '2649',
                                                         '2650', '2852'])])
        for account in accounts:
            account.user_type_id = self.env.ref('l10n_se.type_OvrigaKortfristigaSkulderMoms')

        # Fix  l10n_se.type_Personalkostnader, detta är gjort så att vi kan använda oss av 7331(Skattefria bilersättningar ) som skuld kont när vi har en millersättning utlägg 26/8
        type_personalkostnader = self.env.ref('l10n_se.type_Personalkostnader')
        for acc in self.env['account.account'].search([('user_type_id', '=', type_personalkostnader.id)]):
            acc.reconcile = True
        type_personalkostnader.type = 'payable'

        # Revert these changes
        # Fix  account.data_account_type_current_liabilities, set type to payable and all accounts 25/8 detta är ändrat till payable så att vi kan snappa upp löne spec verfikat när vi gör en payment order. Kanske förstör något annat i odoo.
        OvrigaKortfristigaSkulder = self.env.ref('account.data_account_type_current_liabilities')
        for acc in self.env['account.account'].search([('user_type_id', '=', OvrigaKortfristigaSkulder.id)]):
            acc.reconcile = True
        OvrigaKortfristigaSkulder.type = 'payable'

        # ~ #Todo make so that the correct account types are generated correctly and all account for those types are reconcile. Fix permanent solution for 1000-1900
        account_xml_ids = ['account.data_account_type_current_assets', 'account.data_account_type_non_current_assets',
                           'account.data_account_type_fixed_assets', 'l10n_se.type_TecknatEjInbetaltKapital',
                           'l10n_se.type_HyresratterLiknandeRattigheter'
            , 'l10n_se.type_Goodwill', 'l10n_se.type_ForskottImmateriellaAnlaggningstillgangar',
                           'l10n_se.type_ByggnaderMark', 'l10n_se.type_InventarierVerktygInstallationer',
                           'l10n_se.type_ForbattringsutgifterAnnansFastighet',
                           'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar',
                           'l10n_se.type_PagaendeNyanlaggningarForskottMateriellaAnlaggningstillgangar'
            , 'l10n_se.type_AndelarKoncernforetag', 'l10n_se.type_FordringarKoncernforetagLangfristiga',
                           'l10n_se.type_AndelarIntresseforetagGemensamtStyrdaForetag',
                           'l10n_se.type_FordringarIntresseforetagGemensamtStyrdaForetagLangfristiga',
                           'l10n_se.type_AgarintressenOvrigaForetag',
                           'l10n_se.type_AndraLangfristigaVardepappersinnehav'
            , 'l10n_se.type_LanDelagareNarstaende', 'l10n_se.type_AndraLangfristigaFordringar',
                           'l10n_se.type_LagerRavarorFornodenheter', 'l10n_se.type_LagerVarorUnderTillverkning',
                           'l10n_se.type_LagerFardigaVarorHandelsvaror', 'l10n_se.type_OvrigaLagertillgangar',
                           'l10n_se.type_PagaendeArbetenAnnansRakningOmsattningstillgangar',
                           'l10n_se.type_ForskottTillLeverantorer'
            , 'l10n_se.type_FordringarKoncernforetagKortfristiga',
                           'l10n_se.type_FordringarIntresseforetagGemensamtStyrdaForetagKortfristiga',
                           'l10n_se.type_FordringarOvrigaforetagAgarintresseKortfristiga',
                           'l10n_se.type_UpparbetadEjFaktureradIntakt',
                           'l10n_se.type_ForutbetaldaKostnaderUpplupnaIntakter']
        accounts_types = [self.env.ref(x) for x in account_xml_ids]
        for acctype in accounts_types:
            for acc in self.env['account.account'].search([('user_type_id', '=', acctype.id)]):
                acc.reconcile = True
            acctype.type = 'other'

        # ~ # Denna fanns i listan innan ett tag och blev satt till recievable, men nu ska den vara other igen. 1800-1899
        account_xml_ids = ['l10n_se.type_OvrigaKortfristigaPlaceringar',
                           'l10n_se.type_AndelarKoncernforetagKortfristiga']
        accounts_types = [self.env.ref(x) for x in account_xml_ids]
        for acctype in accounts_types:
            acctype.type = 'other'
            for acc in self.env['account.account'].search([('user_type_id', '=', acctype.id)]):
                acc.reconcile = False

        # 1900 -1999 Denna fanns i listan innan ett tag och blev satt till liquidity, men nu ska den vara other igen.
        account_xml_ids = ['account.data_account_type_liquidity']
        accounts_types = [self.env.ref(x) for x in account_xml_ids]
        for acctype in accounts_types:
            acctype.type = 'liquidity'
            for acc in self.env['account.account'].search([('user_type_id', '=', acctype.id)]):
                if acc.code not in ("1914", "1915", "1916", "1933", "1934"):
                    # if acc.code not in ("1914","1915","1916","1933","1934","1935","1936","1937","1938"): This one was needed on a server, so the amount of odoo created accounts are not set in stone.
                    acc.reconcile = False


# class account_bank_accounts_wizard(models.TransientModel):
#     _inherit = 'account.bank.accounts.wizard'
#
#     account_type = fields.Selection(selection_add=[('bg', 'Bankgiro'), ('pg', 'Plusgiro')])




class AccountInvoice(models.Model):
    # ~ _inherit = 'account.invoice'
    _inherit = 'account.move'

    def set_tax_account(self, tax_name, account_code):
        correct_account = self.env["account.account"].search([("code", "=", account_code)])
        if not correct_account:
            _logger.warning(f"Hittade ingen konto")
            raise UserError(f"Couldnt find account {account_name}")
        _logger.warning(f"{correct_account=}")

        correct_tax = self.env["account.tax"].search([("name", "=", tax_name)])
        if not correct_account:
            _logger.warning(f"Hittade ingen skatt")
            raise UserError(f"Couldnt find tax {tax_name}")
        _logger.warning(f"{correct_tax=}")

        for line in self.line_ids:
            if line.tax_line_id:
                _logger.warning(f"og tax name = {line.tax_line_id.name}")
                if line.account_id:
                    _logger.warning(f"account name = {line.account_id.name}")
                if line.tax_line_id.name == tax_name:
                    _logger.warning(f"Found a match {line.tax_line_id.name} = {tax_name}")
                    line.account_id = correct_account

    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            journal_type = m.invoice_filter_type_domain
            company_id = m.company_id.id or self.env.company.id
            if journal_type:
                domain = [('company_id', '=', company_id), ('type', '=', journal_type)]
            else:
                domain = [('company_id', '=', company_id)]
            m.suitable_journal_ids = self.env['account.journal'].search(domain)


class account_chart_template(models.Model):
    """
        defaults for 4 digits in chart of accounts
     """
    _inherit = 'account.chart.template'

    code_digits = fields.Integer(default=4)
    bas_sru = fields.Binary(string="BAS SRU")
    bas_chart = fields.Binary(string="BAS Chart of Account")
    bas_k2 = fields.Boolean(string='Ej K2', default=True)
    bas_basic = fields.Boolean(string='Endast grundläggande konton', default=True)

    @api.onchange('bas_chart')
    def update_bas_chart(self):
        if not self.bas_chart:
            return

        wb = open_workbook(file_contents=base64.decodestring(self.bas_chart))
        ws = wb.sheet_by_index(0)
        basic_code = u' \u25a0'
        not_k2 = u'[Ej K2]'

        nbr_lines = ws.nrows
        user_type = 'account.data_account_type_asset'

        _logger.warn('Accounts %s' % self.env['account.account.template'].search([('code', 'like', '%.0')]))
        self.env['account.account.template'].search([('code', 'like', '%.0')]).unlink()

        # return
        for l in range(0, ws.nrows):
            if ws.cell_value(l, 2) == 1 or ws.cell_value(l, 2) in range(10, 20) or ws.cell_value(l, 2) in range(1000,
                                                                                                                1999):
                user_type = 'account.data_account_type_asset'
            if ws.cell_value(l, 2) in range(15, 26) or ws.cell_value(l, 2) in range(1500, 1599):
                user_type = 'account.data_account_type_receivable'
            if ws.cell_value(l, 2) in range(1900, 1999):
                user_type = 'account.data_account_type_bank'
            if ws.cell_value(l, 2) == 1910:
                user_type = 'account.data_account_type_cash'

            if ws.cell_value(l, 2) == 2 or ws.cell_value(l, 2) in range(20, 30) or ws.cell_value(l, 2) in range(2000,
                                                                                                                2999):
                user_type = 'account.data_account_type_liability'
            if ws.cell_value(l, 2) == 20 or ws.cell_value(l, 2) in range(2000, 2050):
                user_type = 'account.conf_account_type_equity'
            if ws.cell_value(l, 2) in [23, 24] or ws.cell_value(l, 2) in range(2300, 2700):
                user_type = 'account.data_account_type_payable'
            if ws.cell_value(l, 2) in [26, 27] or ws.cell_value(l, 2) in range(2600, 2800):
                user_type = 'account.conf_account_type_tax'

            if ws.cell_value(l, 2) == 3 or ws.cell_value(l, 2) == '30-34' or ws.cell_value(l, 2) in range(30,
                                                                                                          40) or ws.cell_value(
                    l, 2) in range(3000, 4000):
                user_type = 'account.data_account_type_income'
            if ws.cell_value(l, 2) in [4, 5, 6, 7] or ws.cell_value(l, 2) in ['5-6'] or ws.cell_value(l, 2) in range(30,
                                                                                                                     80) or ws.cell_value(
                    l, 2) in ['40-45'] or ws.cell_value(l, 2) in range(4000, 8000):
                user_type = 'account.data_account_type_expense'

            if ws.cell_value(l, 2) == 8 or ws.cell_value(l, 2) in [80, 81, 82, 83] or ws.cell_value(l, 2) in range(8000,
                                                                                                                   8400):
                user_type = 'account.data_account_type_income'
            if ws.cell_value(l, 2) in [84, 88] or ws.cell_value(l, 2) in range(8400, 8500) or ws.cell_value(l,
                                                                                                            2) in range(
                    8800, 8900):
                user_type = 'account.data_account_type_expense'
            if ws.cell_value(l, 2) in [89] or ws.cell_value(l, 2) in range(8900, 9000):
                user_type = 'account.data_account_type_expense'

            if ws.cell_value(l, 2) in range(1, 9) or ws.cell_value(l, 2) in ['5-6']:  # kontoklass
                last_account_class = self.env['account.account.template'].create({
                    'code': ws.cell_value(l, 2),
                    'name': ws.cell_value(l, 3),
                    'user_type': self.env.ref(user_type).id,
                    'type': 'view',
                    'chart_template_id': self.id,
                })
            if ws.cell_value(l, 2) in range(10, 99) or ws.cell_value(l, 2) in ['30-34', '40-45']:  # kontogrupp
                last_account_group = self.env['account.account.template'].create(
                    {
                        'code': ws.cell_value(l, 2),
                        'name': ws.cell_value(l, 3),
                        'type': 'view',
                        'user_type': self.env.ref(user_type).id,
                        'parent_id': last_account_class.id,
                        'chart_template_id': self.id,
                    })

            if ws.cell_value(l, 2) in range(1000, 9999):
                last_account = self.env['account.account.template'].create({
                    'code': ws.cell_value(l, 2),
                    'name': ws.cell_value(l, 3),
                    'type': 'other',
                    'parent_id': last_account_group.id,
                    'user_type': self.env.ref(user_type).id,
                    'chart_template_id': self.id,
                    'bas_k34': True if ws.cell_value(l, 1) == not_k2 else False,
                    'bas_basic': True if ws.cell_value(l, 1) == basic_code else False,
                })
                if ws.cell_value(l, 5) in range(1000, 9999):
                    last_account = self.env['account.account.template'].create({
                        'code': ws.cell_value(l, 5),
                        'name': ws.cell_value(l, 6),
                        'type': 'other',
                        'parent_id': last_account_group.id,
                        'user_type': self.env.ref(user_type).id,
                        'chart_template_id': self.id,
                        'bas_k34': True if ws.cell_value(l, 4) == not_k2 else False,
                        'bas_basic': True if ws.cell_value(l, 4) == basic_code else False,
                    })

            # ~ if ws.cell_value(l,1) == basic_code and self.bas_basic:
            # ~ _logger.warn("%s %s" % (ws.cell_value(l,2),ws.cell_value(l,3)))
            # ~ for account_l in range(l,ws.nrows):
            # ~ if ws.cell_value(l,4) == basic_code:
            # ~ _logger.warn("%s %s" % (ws.cell_value(l,5),ws.cell_value(l,6)))
            # ~ if ws.cell_value(l,2) > 0:
            # ~ break

    


class account_account_template(models.Model):
    _inherit = "account.account.template"

    bas_k34 = fields.Boolean(string='K3/K4', default=False)
    bas_basic = fields.Boolean(string='Endast grundläggande konton', default=True)


class account_tax_template(models.Model):
    _inherit = 'account.tax.template'

    def account2tax_ids(self, account_code):
        tax_ids = []
        #        if user_type == 'account.data_account_type_income':
        if account_code in range(3000, 3670):
            tax_ids = [(6, 0, [self.env['account.tax.template'].search([('description', '=', 'MP1')])[0].id])]
        if account_code in [3002, 3402]:
            tax_ids = [(6, 0, [self.env['account.tax.template'].search([('description', '=', 'MP2')])[0].id])]
        if account_code in [3003, 3403]:
            tax_ids = [(6, 0, [self.env['account.tax.template'].search([('description', '=', 'MP3')])[0].id])]
        if account_code in [3004, 3100, 3105, 3108, 3404]:
            tax_ids = []
        #        if user_type == 'account.data_account_type_expense':
        if account_code in range(4000, 4600):
            tax_ids = [(6, 0, [self.env['account.tax.template'].search([('description', '=', 'I')])[0].id])]
        if account_code in [4516, 4532, 4536, 4546]:
            tax_ids = [(6, 0, [self.env['account.tax.template'].search([('description', '=', 'I12')])[0].id])]
        if account_code in [4517, 4533, 4537, 4547]:
            tax_ids = [(6, 0, [self.env['account.tax.template'].search([('description', '=', 'I6')])[0].id])]
        if account_code in [4518, 4538]:
            tax_ids = []
        if account_code in range(5000, 6600):
            tax_ids = [(6, 0, [self.env['account.tax.template'].search([('description', '=', 'I')])[0].id])]
        if account_code in [5810]:
            tax_ids = [(6, 0, [self.env['account.tax.template'].search([('description', '=', 'I6')])[0].id])]
        return tax_ids


class account_account_type(models.Model):
    _inherit = 'account.account.type'

    name = fields.Char(string='Account Type', required=True, translate=False)
    element_name = fields.Char(string='Element Name', help='This name is used as tag in xbrl-file.')
    account_range = fields.Char(string='Accoun Range', help='Domain shows which account should has this account type.')
    main_type = fields.Selection(selection=[
        ('RorelsensIntakterLagerforandringarMmAbstract', u'Rörelseintäkter, lagerförändringar m.m.'),
        ('RorelsekostnaderAbstract', u'Rörelsekostnader'),
        ('FinansiellaPosterAbstract', u'Finansiella poster'),
        ('BokslutsdispositionerAbstract', u'Bokslutsdispositioner'),
        ('SkatterAbstract', u'Skatter'),
        ('TillgangarAbstract', u'Tillgångar'),
        ('EgetKapitalSkulderAbstract', u'Eget kapital och skulder'),
    ], string='Main Type')
    report_type = fields.Selection(selection=[('r', u'Resultaträkning'), ('b', u'Balansräkning')], string='Report Type')

    # key: element_name
    # value: name
    name_exchange_dict = {
        'Kundfordringar': u'Kundfordringar',
        'Leverantorsskulder': u'Leverantörsskulder',
        'KassaBankExklRedovisningsmedel': u'Kassa och bank exklusive redovisningsmedel',
        'CheckrakningskreditKortfristig': u'Kortfristig checkräkningskredit',
        'OvrigaFordringarKortfristiga': u'Övriga kortfristga fordringar',
        'KoncessionerPatentLicenserVarumarkenLiknandeRattigheter': u'Koncessioner, patent, licenser, varumärken samt liknande rättigheter',
        'ForskottFranKunder': u'Förskott från kunder',
        'MaskinerAndraTekniskaAnlaggningar': u'Maskiner och andra tekniska anläggningar',
        'OvrigaKortfristigaSkulder': u'Övriga kortfristiga skulder',
        'OvrigaLangfristigaSkulderKreditinstitut': u'Övriga långfristiga skulder till kreditinstitut',
        'Aktiekapital': u'Aktiekapital',
        'AretsResultat': u'Årets resultat',
        'OvrigaRorelseintakter': u'Övriga rörelseintäkter',
        'Nettoomsattning': u'Nettoomsättning',
        'AvskrivningarNedskrivningarMateriellaImmateriellaAnlaggningstillgangar': u'Av- och nedskrivningar av materiella och immateriella anläggningstillgångar',
        'OvrigaRorelsekostnader': u'Övriga rörelsekostnader',
        'HandelsvarorKostnader': u'Kostnad för sålda handelsvaror',
    }

    # Change account type names from core(account)
    @api.model
    def _change_name(self):
        for k, v in self.name_exchange_dict.items():
            self.env['account.account.type'].search([('element_name', '=', k)]).write({'name': v})

    @api.model
    def set_account_type(self):
        for record in self:
            for account in self.env['account.account'].search(eval(record.account_range)):
                if account.user_type_id != record:
                    account.user_type_id = record
                    _logger.warn('Account %s set type to %s' % (account.name, record.name))

    @api.model
    def return_eval(self):
        return eval

        # for action:
        # ~ o = env['account.account.type'].browse([9])
        # ~ ids = [a['id'] for a in env['account.account'].search_read([('user_type_id', 'in', [a.id for a in o])], ['id'])]
        # ~ sql = "UPDATE account_account SET reconcile = true WHERE id IN %s;"
        # ~ env.cr.execute(sql, [tuple(ids)])
        # ~ o.write({'type': 'payable'})

    # ~ @api.multi
    def get_account_range(self):
        self.ensure_one()
        return self.env['account.account'].search(eval(self.account_range))

    def account2user_type(self, account_code):
        user_type = 'account.data_account_type_asset'
        if account_code == 1 or account_code in range(10, 20) or account_code in range(1000, 1999):
            user_type = 'account.data_account_type_asset'
        if account_code in range(15, 26) or account_code in range(1500, 1599):
            user_type = 'account.data_account_type_receivable'
        if account_code in range(1900, 1999):
            user_type = 'account.data_account_type_bank'
        if account_code == 1910:
            user_type = 'account.data_account_type_cash'

        if account_code == 2 or account_code in range(20, 30) or account_code in range(2000, 2999):
            user_type = 'account.data_account_type_liability'
        if account_code == 20 or account_code in range(2000, 2050):
            user_type = 'account.conf_account_type_equity'
        if account_code in [23, 24] or account_code in range(2300, 2700):
            user_type = 'account.data_account_type_payable'
        if account_code in [26, 27] or account_code in range(2600, 2800):
            user_type = 'account.conf_account_type_tax'

        if account_code == 3 or account_code == '30-34' or account_code in range(30, 40) or account_code in range(3000,
                                                                                                                  4000):
            user_type = 'account.data_account_type_income'
        if account_code in [4, 5, 6, 7] or account_code in ['5-6'] or account_code in range(30, 80) or account_code in [
            '40-45'] or account_code in range(4000, 8000):
            user_type = 'account.data_account_type_expense'

        if account_code == 8 or account_code in [80, 81, 82, 83] or account_code in range(8000, 8400):
            user_type = 'account.data_account_type_income'
        if account_code in [84, 88] or account_code in range(8400, 8500) or account_code in range(8800, 8900):
            user_type = 'account.data_account_type_expense'
        if account_code in [89] or account_code in range(8900, 9000):
            user_type = 'account.data_account_type_expense'
        return self.env.ref(user_type) if user_type else None

    def _account_type_lookup(self, code=False):
        if code:
            account_type_ids = self.env['account.account.type'].search([('account_range', '!=', False)],limit=1)
            type_list = account_type_ids.filtered(lambda xd: str(code) in eval(xd.account_range)[0][-1])
            return type_list
        else:
            return False


# class account_financial_report(models.Model):
#     _inherit = 'account.financial.report'
#
#     element_name = fields.Char(string='Element Name', help='This name is used as tag in xbrl-file.')
#     version_name = fields.Char(string='Version Name', help='This name is from import file.')


class Company(models.Model):
    _inherit = 'res.company'

    @api.model
    def account_chart_func(self):
        # ~ company = self.env.ref('base.main_company')
        company = self.env.user.company_id
        if not company.chart_template_id:
            sek = self.env.ref('base.SEK')
            sek.active = True
            self.env.currency_id = sek
            config = self.env['res.config.settings'].create({})
            config.chart_template_id = self.env.ref('l10n_se.chart_template_K2_2017')
            config.chart_template_id.try_loading()
            config.set_values()
            year = datetime.today().strftime("%Y")
            fy = self.env['account.fiscalyear'].create({
                'name': year,
                'code': year,
                'date_start': '%s-01-01' % year,
                'date_stop': '%s-12-31' % year,
                'state': 'draft',
            })
            fy.create_period1()


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    def _load(self, sale_tax_rate, purchase_tax_rate, company):
        res = super(AccountChartTemplate, self)._load(sale_tax_rate, purchase_tax_rate, company)
        _logger.warning("load"*100)
        _logger.warning(f"{company=}, {self.env.company=}")
        loner_till_tjansteman_7210 = self.env['account.account'].search([('code', '=', '7210'),("company_id","=",company.id)])
        lon_vaxa_stod_tjansteman = self.env['account.account'].search([('code', '=', '7213'),("company_id","=",company.id)])
        loner_till_tjansteman_16_36 = self.env['account.account'].search([('code', '=', '7214'),("company_id","=",company.id)])
        loner_till_tjansteman_6_15 = self.env['account.account'].search([('code', '=', '7215'),("company_id","=",company.id)])
        avrakning_lagstadgade_sociala_avgifter = self.env['account.account'].search([('code', '=', '2731'),("company_id","=",company.id)])
        avrakning_sarskild_loneskatt = self.env['account.account'].search([('code', '=', '2732'),("company_id","=",company.id)])
        personalskatt = self.env['account.account'].search([('code', '=', '2710'),("company_id","=",company.id)])
        account_values = {
            'UlagAvgHel': {'invoice_repartition_line_ids': [(5, 0, 0), (
            0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                  'repartition_type': 'tax',
                                                                                  'account_id': loner_till_tjansteman_7210.id, }), ],
                           'refund_repartition_line_ids': [(5, 0, 0), (
                           0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                                 'repartition_type': 'tax',
                                                                                                 'account_id': loner_till_tjansteman_7210.id, }), ]},
            'UlagVXLon': {'invoice_repartition_line_ids': [(5, 0, 0), (
            0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                  'repartition_type': 'tax',
                                                                                  'account_id': lon_vaxa_stod_tjansteman.id, }), ],
                          'refund_repartition_line_ids': [(5, 0, 0),
                                                          (0, 0, {'factor_percent': 100, 'repartition_type': 'base', }),
                                                          (0, 0, {'factor_percent': 100, 'repartition_type': 'tax',
                                                                  'account_id': lon_vaxa_stod_tjansteman.id, }), ]},
            'UlagAvgAldersp': {'invoice_repartition_line_ids': [(5, 0, 0), (
            0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                  'repartition_type': 'tax',
                                                                                  'account_id': loner_till_tjansteman_16_36.id, }), ],
                               'refund_repartition_line_ids': [(5, 0, 0), (
                               0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0,
                                                                                              {'factor_percent': 100,
                                                                                               'repartition_type': 'tax',
                                                                                               'account_id': loner_till_tjansteman_16_36.id, }), ]},
            'UlagAlderspSkLon': {'invoice_repartition_line_ids': [(5, 0, 0), (
            0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                  'repartition_type': 'tax',
                                                                                  'account_id': loner_till_tjansteman_6_15.id, }), ],
                                 'refund_repartition_line_ids': [(5, 0, 0), (
                                 0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0,
                                                                                                {'factor_percent': 100,
                                                                                                 'repartition_type': 'tax',
                                                                                                 'account_id': loner_till_tjansteman_6_15.id, }), ]},
            'AvgHel': {'invoice_repartition_line_ids': [(5, 0, 0),
                                                        (0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (
                                                        0, 0, {'factor_percent': 100, 'repartition_type': 'tax',
                                                               'account_id': avrakning_lagstadgade_sociala_avgifter.id, }), ],
                       'refund_repartition_line_ids': [(5, 0, 0),
                                                       (0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (
                                                       0, 0, {'factor_percent': 100, 'repartition_type': 'tax',
                                                              'account_id': avrakning_lagstadgade_sociala_avgifter.id, }), ]},
            'AvgVXLon': {'invoice_repartition_line_ids': [(5, 0, 0),
                                                          (0, 0, {'factor_percent': 100, 'repartition_type': 'base', }),
                                                          (0, 0, {'factor_percent': 100, 'repartition_type': 'tax',
                                                                  'account_id': avrakning_sarskild_loneskatt.id, }), ],
                         'refund_repartition_line_ids': [(5, 0, 0),
                                                         (0, 0, {'factor_percent': 100, 'repartition_type': 'base', }),
                                                         (0, 0, {'factor_percent': 100, 'repartition_type': 'tax',
                                                                 'account_id': avrakning_sarskild_loneskatt.id, }), ]},
            'AvgAldersp': {'invoice_repartition_line_ids': [(5, 0, 0), (
            0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                  'repartition_type': 'tax',
                                                                                  'account_id': avrakning_lagstadgade_sociala_avgifter.id, }), ],
                           'refund_repartition_line_ids': [(5, 0, 0), (
                           0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                                 'repartition_type': 'tax',
                                                                                                 'account_id': avrakning_lagstadgade_sociala_avgifter.id, }), ]},
            'AvgAlderspSkLon': {'invoice_repartition_line_ids': [(5, 0, 0), (
            0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                  'repartition_type': 'tax',
                                                                                  'account_id': avrakning_lagstadgade_sociala_avgifter.id, }), ],
                                'refund_repartition_line_ids': [(5, 0, 0), (
                                0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0,
                                                                                               {'factor_percent': 100,
                                                                                                'repartition_type': 'tax',
                                                                                                'account_id': avrakning_lagstadgade_sociala_avgifter.id, }), ]},
            'AgPre': {'invoice_repartition_line_ids': [(5, 0, 0),
                                                       (0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (
                                                       0, 0, {'factor_percent': 100, 'repartition_type': 'tax',
                                                              'account_id': personalskatt.id, }), ],
                      'refund_repartition_line_ids': [(5, 0, 0),
                                                      (0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (
                                                      0, 0, {'factor_percent': 100, 'repartition_type': 'tax',
                                                             'account_id': personalskatt.id, }), ]},
            'SkAvdrLon': {'invoice_repartition_line_ids': [(5, 0, 0), (
            0, 0, {'factor_percent': 100, 'repartition_type': 'base', }), (0, 0, {'factor_percent': 100,
                                                                                  'repartition_type': 'tax',
                                                                                  'account_id': personalskatt.id, }), ],
                          'refund_repartition_line_ids': [(5, 0, 0),
                                                          (0, 0, {'factor_percent': 100, 'repartition_type': 'base', }),
                                                          (0, 0, {'factor_percent': 100, 'repartition_type': 'tax',
                                                                  'account_id': personalskatt.id, }), ]},
        }

        for k, v in account_values.items():
            self.env['account.tax'].search([('name', '=', k),("company_id","=",company.id)]).write(v)

        # self.env['account.account'].fix_account_types()
        return res
