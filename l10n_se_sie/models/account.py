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
        _logger.warning("account journal export sie")
        return self.env['account.sie'].export_sie(ver_ids)


class account_move(models.Model):
    _inherit = 'account.move'
    
    is_incoming_balance_move = fields.Boolean(default = False)

    def export_sie(self):
        # ~ ver_ids = self.env['account.move'].search([('id','in',ids)])
        return self.env['account.sie'].export_sie(self)
        
class AccountChartTemplate(models.Model):
    _inherit = 'account.account'

    @api.model
    def fix_account_types_skf(self):
       value_list = [{'code': 1010, 'name': 'Balanserade utgifter', 'user_type_id': 'account.data_account_type_non_current_assets'}, {'code': 1018, 'name': 'Ack nedskrivningar balanserade utg', 'user_type_id': 'account.data_account_type_non_current_assets'}, {'code': 1019, 'name': 'Ack avskrivningar balanserade utg', 'user_type_id': 'account.data_account_type_non_current_assets'}, {'code': 1031, 'name': 'Produktutveckling', 'user_type_id': 'account.data_account_type_non_current_assets'}, {'code': 1032, 'name': 'Bidrag utv', 'user_type_id': 'account.data_account_type_non_current_assets'}, {'code': 1053, 'name': 'Övriga immateriella rättigheter', 'user_type_id': 'account.data_account_type_non_current_assets'}, {'code': 1226, 'name': 'Bidrag', 'user_type_id': 'l10n_se.type_InventarierVerktygInstallationer'}, {'code': 1260, 'name': 'Leasade tillgångar', 'user_type_id': 'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar'}, {'code': 1261, 'name': 'Leasade tillgångar - Hyreskontrakt', 'user_type_id': 'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar'}, {'code': 1262, 'name': 'Leasade tillgångar - Fordon', 'user_type_id': 'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar'}, {'code': 1263, 'name': 'Leasade tillgångar - Truckar', 'user_type_id': 'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar'}, {'code': 1269, 'name': 'Ack avskrivningar på leasingavtal', 'user_type_id': 'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar'}, {'code': 1271, 'name': 'Ack avskr - leasade hyreskontrakt', 'user_type_id': 'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar'}, {'code': 1272, 'name': 'Ack avskr - leasade fordon', 'user_type_id': 'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar'}, {'code': 1273, 'name': 'Ack avskr - leasade truckar', 'user_type_id': 'l10n_se.type_OvrigaMateriellaAnlaggningstillgangar'}, {'code': 1362, 'name': 'Fordringar dotterbolag', 'user_type_id': 'l10n_se.type_LanDelagareNarstaende'}, {'code': 1370, 'name': 'Uppskjuten skattefordran', 'user_type_id': 'account.data_account_type_current_assets'}, {'code': 1390, 'name': 'Värderegl långfr fordr', 'user_type_id': 'l10n_se.type_AndraLangfristigaFordringar'}, {'code': 1400, 'name': 'Lager', 'user_type_id': 'l10n_se.type_LagerRavarorFornodenheter'}, {'code': 1515, 'name': 'Osäkra kundfordringar', 'user_type_id': 'account.data_account_type_receivable'}, {'code': 1517, 'name': 'Kvittning kundfaktura', 'user_type_id': 'account.data_account_type_receivable'}, {'code': 1869, 'name': 'Värderegl finans instr', 'user_type_id': 'l10n_se.type_OvrigaKortfristigaPlaceringar'}, {'code': 1941, 'name': 'SEB Valutakonto EUR', 'user_type_id': 'account.data_account_type_liquidity'}, {'code': 1942, 'name': 'Bankkonto Försäkringsgirot', 'user_type_id': 'account.data_account_type_liquidity'}, {'code': 1951, 'name': 'Handelsbanken Sparkonto', 'user_type_id': 'account.data_account_type_liquidity'}, {'code': 1952, 'name': 'Konto SBAB', 'user_type_id': 'account.data_account_type_liquidity'}, {'code': 1953, 'name': 'Handelsbanken E-konto', 'user_type_id': 'account.data_account_type_liquidity'}, {'code': 2113, 'name': 'Periodiseringsfond TAX 2013', 'user_type_id': 'l10n_se.type_Periodiseringsfonder'}, {'code': 2117, 'name': 'Periodiseringsfond TAX 97', 'user_type_id': 'l10n_se.type_Periodiseringsfonder'}, {'code': 2118, 'name': 'Periodiseringsfond TAX 98', 'user_type_id': 'l10n_se.type_Periodiseringsfonder'}, {'code': 2119, 'name': 'Periodiseringsfond TAX 99', 'user_type_id': 'l10n_se.type_Periodiseringsfonder'}, {'code': 2124, 'name': 'Periodiseringsfond 2014', 'user_type_id': 'l10n_se.type_Periodiseringsfonder'}, {'code': 2195, 'name': 'Valutakursreserv', 'user_type_id': 'l10n_se.type_OvrigaObeskattadeReserver'}, {'code': 2211, 'name': 'Avsättningar för PRI-pensioner', 'user_type_id': 'l10n_se.type_OvrigaAvsattningarPensionerLiknandeForpliktelser'}, {'code': 2219, 'name': 'Avsättningar för övr pensioner', 'user_type_id': 'l10n_se.type_OvrigaAvsattningarPensionerLiknandeForpliktelser'}, {'code': 2240, 'name': 'Avsättningar för uppskjutna skatter', 'user_type_id': 'l10n_se.type_OvrigaAvsattningar'}, {'code': 2374, 'name': 'Långfristig skuld avseende leasingkontrakt', 'user_type_id': 'l10n_se.type_OvrigaLangfristigaSkulder'}, {'code': 2398, 'name': 'Kortfristig del av långfr skuld', 'user_type_id': 'account.data_account_type_current_liabilities'}, {'code': 2449, 'name': 'Kvittning av leverantörsfakturor', 'user_type_id': 'account.data_account_type_payable'}, {'code': 2733, 'name': 'Avräkn särskild sjukförsäkringsavg', 'user_type_id': 'account.data_account_type_current_liabilities'}, {'code': 2776, 'name': 'Långfristig del VD kostnader', 'user_type_id': 'l10n_se.type_OvrigaLangfristigaSkulder'}, {'code': 2842, 'name': 'Kortfristig skuld avseende leasingkontrakt', 'user_type_id': 'account.data_account_type_current_liabilities'}, {'code': 2843, 'name': 'Avstämningskonto leasingkontrakt', 'user_type_id': 'account.data_account_type_current_liabilities'}, {'code': 2896, 'name': 'Kortfristig skuld aktieägare', 'user_type_id': 'account.data_account_type_current_liabilities'}, {'code': 2901, 'name': 'Upplupna löner VD', 'user_type_id': 'l10n_se.type_UpplupnaKostnaderForutbetaldaIntakter'}, {'code': 2921, 'name': 'Upplupna soc.avg sem.lön', 'user_type_id': 'l10n_se.type_UpplupnaKostnaderForutbetaldaIntakter'}, {'code': 2945, 'name': 'Beräkn upplupna särskild sjukförsäkringsavgift', 'user_type_id': 'l10n_se.type_UpplupnaKostnaderForutbetaldaIntakter'}, {'code': 2995, 'name': 'Skuld inkomna följesedlar', 'user_type_id': 'l10n_se.type_UpplupnaKostnaderForutbetaldaIntakter'}, {'code': 3008, 'name': 'Försäljning olja EU kod 38 (SKF)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3011, 'name': 'Försäljning olja 25% (Ext)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3020, 'name': 'Försäljning VMB varor', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3028, 'name': 'Positiv VM omföringskonto', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3030, 'name': 'Positiv VM', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3041, 'name': 'Kemi (externa kunder) 25% SV', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3042, 'name': 'Försäljn tjänst 12% sv', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3043, 'name': 'Försäljn tjänst 6% sv', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3044, 'name': 'Försäljn momsfri', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3045, 'name': 'Förstudier utanför EU', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3046, 'name': 'Försäljn tjänst till EU', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3048, 'name': 'Försäljn tjänst EU momsfri', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3049, 'name': 'Försäljn momsfritt DST (ext)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3050, 'name': 'DST Unit (externa kunder) 25% Sv', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3051, 'name': 'Fakturerade kostnader (Ext kund)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3052, 'name': 'DST Unit utanför EU (SKF)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3053, 'name': 'DST Unit inom EU 35 (SKF)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3054, 'name': 'Försäljning DST maskin SKF  moms 25%', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3055, 'name': 'Kemi utanför EU (SKF)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3056, 'name': 'Kemi inom EU land (SKF)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3057, 'name': 'DST Unit - Treparts försälj till EU', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3058, 'name': 'Försäljning tjänster momsfri', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3059, 'name': 'Försäljning kemi -Treparts försälj till EU (SKF)', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3061, 'name': 'Ragnsell Rocco', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3062, 'name': 'Rocco Slop', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3063, 'name': 'DST Unit - (extern kund) 25% SV', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3099, 'name': 'Intäktskonto periodisering', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3736, 'name': 'Kassarabatter export', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3737, 'name': 'Kassarabatter EU', 'user_type_id': 'account.data_account_type_revenue'}, {'code': 3940, 'name': 'Oreal neg/pos värdeföränd säkringsinstr', 'user_type_id': 'account.data_account_type_other_income'}, {'code': 3974, 'name': 'Vinst avyttr bilar och transportmedel', 'user_type_id': 'account.data_account_type_other_income'}, {'code': 4007, 'name': 'Mtrl - Inköp kemi (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4008, 'name': 'Mtrl - Inköp olja (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4009, 'name': 'Mtrl - Inköp kemi (Ext kund)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4010, 'name': 'Mtrl - inköp POC (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4011, 'name': 'Mtrl - Inköp Olja (Ext kund)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4012, 'name': 'Mtrl - Inköp DST', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4013, 'name': 'Mtrl - Processutrustning (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4014, 'name': 'Mtrl - El', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4015, 'name': 'Mtrl - Rör', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4016, 'name': 'Mtrl - Automation (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4017, 'name': 'Mtrl - Stål/Byggnad', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4020, 'name': 'Inköp VMB varor', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4028, 'name': 'Negativ VM omföringskonto', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4030, 'name': 'Negativ VM', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4050, 'name': 'Mtrl-Utveckling processutrustning (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4051, 'name': 'Mtrl - Inköp Olja (Ext kund) från EU (ej gräns)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4055, 'name': 'Inköp underleverantör fakt EDC', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4056, 'name': 'Inköp  tjänst EU (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4057, 'name': 'Inköp varor 12% EU', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4058, 'name': 'Inköp  tjänst EU (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4100, 'name': 'Kostn uthyrn lokal sk.pl', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4113, 'name': 'Mtrl - Processutrustning (Ext kund)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4156, 'name': 'Mtrl - Förbrukningsmaterial maskiner', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4549, 'name': 'Motkonto beskattningsunderlag import', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4601, 'name': 'Analystjänster (EXT)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4614, 'name': 'U.E - El (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4615, 'name': 'U.E - Rör', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4616, 'name': 'U.E - Automation (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4617, 'name': 'U.E - Stål/Byggnad', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4618, 'name': 'U.E - konstruktion (SKF)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4619, 'name': 'U.E - Projektering', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4620, 'name': 'U.E - Installation (EXT)', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4710, 'name': 'Fraktkostnader', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4810, 'name': 'Tull- och speditionskostnader m.m vid import', 'user_type_id': 'l10n_se.type_RavarorFornodenheterKostnader'}, {'code': 4971, 'name': 'Förändr påg arbete( Ext kund)', 'user_type_id': 'l10n_se.type_ForandringLagerProdukterIArbeteFardigaVarorPagaendeArbetenAnnansRakning'}, {'code': 4990, 'name': 'Lagerförändring', 'user_type_id': 'account.data_account_type_direct_costs'}, {'code': 5459, 'name': 'Förbruknigsmaterial inköp EU', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 5461, 'name': 'Förbrukning olja/kemi internt', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 5711, 'name': 'Fraktkostnader internt SKF', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 5991, 'name': 'Marknadsundersökningar mm utanför EU', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6541, 'name': 'Allocated IT Central cost', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6542, 'name': 'Allocated IT Direct', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6543, 'name': 'Direkfakturerade IT kostnader SKF', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6551, 'name': 'Konsultarvoden SKF', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6552, 'name': 'Konsultarvoden Manualer', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6595, 'name': 'Övriga kostnader Ånge', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6596, 'name': 'Kostnader Ånge förs/straffavgift', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6600, 'name': 'Köpta tjänster koncernföretag', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6601, 'name': 'Rotterdam', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6602, 'name': 'IME aktiviteter', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 6921, 'name': 'Utvecklingskostnader konsulter', 'user_type_id': 'l10n_se.type_OvrigaExternaKostnader'}, {'code': 7001, 'name': 'Återföring lön VD', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7002, 'name': 'AIG på återförd lön VD', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7014, 'name': 'Löner till kollektivanställda 16,36%', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7015, 'name': 'Löner till kollektivanställda 6,15%', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7214, 'name': 'Komptid ATF', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7215, 'name': 'Löner till tjänstemän 6,15%', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7224, 'name': 'Löner till företagsledare 16,36%', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7225, 'name': 'Löner till företagsledare 6,15%', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7338, 'name': 'Skattepliktig ers trängselskatt', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7398, 'name': 'Förmån', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7399, 'name': 'Motkontering av förmån', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7491, 'name': 'Övriga avgifter PRI', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7520, 'name': 'Arb.giv.avgifter 16,36%', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7521, 'name': 'Avgifter för löner och ersättningar', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7534, 'name': 'Särskild löneskatt förvärvsinkomster 6,15%', 'user_type_id': 'l10n_se.type_Personalkostnader'}, {'code': 7822, 'name': 'Avskrivn byggnadsinv', 'user_type_id': 'account.data_account_type_depreciation'}, {'code': 7841, 'name': 'Avskr leasade hyreskontrakt', 'user_type_id': 'account.data_account_type_depreciation'}, {'code': 7842, 'name': 'Avskr leasade fordon', 'user_type_id': 'account.data_account_type_depreciation'}, {'code': 7843, 'name': 'Avksr leasade truckar', 'user_type_id': 'account.data_account_type_depreciation'}, {'code': 7932, 'name': 'Avskrivningar hyresrätt', 'user_type_id': 'account.data_account_type_depreciation'}, {'code': 7940, 'name': 'Oreal pos/neg värdeföränd säkringsinstr', 'user_type_id': 'account.data_account_type_expenses'}, {'code': 7974, 'name': 'Förlust avyttr aktier/andel', 'user_type_id': 'account.data_account_type_expenses'}, {'code': 7989, 'name': 'Övriga kostn naturaförm', 'user_type_id': 'account.data_account_type_expenses'}, {'code': 8014, 'name': 'Koncernbidrag', 'user_type_id': 'l10n_se.type_ResultatAndelarKoncernforetag'}, {'code': 8019, 'name': 'Övriga utdelningar på andelar koncernföretag', 'user_type_id': 'l10n_se.type_ResultatAndelarKoncernforetag'}, {'code': 8021, 'name': 'Resultat vid försälning av aktier', 'user_type_id': 'l10n_se.type_ResultatAndelarKoncernforetag'}, {'code': 8291, 'name': 'Orealiserade värdeförändring anläggningstillgångar', 'user_type_id': 'l10n_se.type_ResultatOvrigaFinansiellaAnlaggningstillgangar'}, {'code': 8295, 'name': 'Orealiserade värdeförändring derivatinstrument', 'user_type_id': 'l10n_se.type_ResultatOvrigaFinansiellaAnlaggningstillgangar'}, {'code': 8300, 'name': 'Ränteintäkter', 'user_type_id': 'l10n_se.type_OvrigaRanteintakterLiknandeResultatposter'}, {'code': 8320, 'name': 'Värdering till verkligt värde, oms tillg', 'user_type_id': 'l10n_se.type_OvrigaRanteintakterLiknandeResultatposter'}, {'code': 8321, 'name': 'Orealiserade värdeföränd omsättn tillg', 'user_type_id': 'l10n_se.type_OvrigaRanteintakterLiknandeResultatposter'}, {'code': 8325, 'name': 'Orealiserade värdeföränd derivat', 'user_type_id': 'l10n_se.type_OvrigaRanteintakterLiknandeResultatposter'}, {'code': 8401, 'name': 'Räntekostnad avseende leasing', 'user_type_id': 'l10n_se.type_RantekostnaderLiknandeResultatposter'}, {'code': 8451, 'name': 'Orealiserade värdeförändringar på skulder', 'user_type_id': 'l10n_se.type_RantekostnaderLiknandeResultatposter'}, {'code': 8897, 'name': 'Återföring av SURV', 'user_type_id': 'l10n_se.type_OvrigaBokslutsdispositioner'}, {'code': 8940, 'name': 'Uppskjuten skatt', 'user_type_id': 'l10n_se.type_OvrigaSkatter'}]
       for account_dict in value_list:
            created_account = self.env['account.account'].search([('code','=',account_dict['code'])])
            _logger.warning(created_account)
            if not created_account:
                account_type_id = self.env.ref(account_dict['user_type_id'])
                _logger.warning(f"{account_type_id=}")
                if account_type_id.type == 'receivable' or account_type_id.type == 'payable':
                    account_dict['reconcile'] = True
                _logger.warning(f"{account_dict=}")
                account_dict['user_type_id'] = account_type_id.id
                _logger.warning(f"{account_dict=}")
                self.env['account.account'].create(account_dict)

   
                    
                    

