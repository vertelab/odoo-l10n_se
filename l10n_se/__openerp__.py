# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Vertel (<http://www.vertel.se>).
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


{
    'name': 'Sweden - Accounting',
    'version': '0.11',
    'category': 'Localization/Account Charts',
    'description': """Sweden - Chart of accounts

        * BAS 2015 K1 (Minimal chart of account, rules from SKV-283 v16)
        * BAS 2015 (K2-K4, follows INK2R-form and rules in SKV-294 v11)
        * Tax-codes from SKV-4700 r1-49  SKV-409

        BAS 2015 K1 and BAS 2015 in original can be found at www.bas.se.
        When you creats your companies, don't forget to change currency to SEK. 
        Usually you want tax-code MP1 and I for standard sales and purchases, 
        MP2, MP3 and I12/I6 are for products and services with 12 % and 6 % tax.
        You also may want to change the automatic created bank accounts to what
        accounts you want to associate them to.
        
        BFN (Bokföringsnämden) are working with accounting regulations for unlisted
        SME-companies in Sweden. The basis are K3 that will be finalized in 2013, K1 
        and K2 are derived from K3 with a numerous of simplifications.

        * K1 are sole traders with a turnover under 3 MSEK and can use a simplified 
          year end.
        * K2 are small companies and associations that doesn't pass more than one 
          of three limits two years in a row: not more than 50 employees in average, assets 
          worth more than 40 MSEK, not more than 80 MSEK in turnover.
        * K3 are an unlisted company that passes two or more of theese limits.
        * K4 are an enlisted public company.
        
        K1 and K2 are not obliged to use an external auditor (turn over under 80 MSEK), using 
        BAS 2015 K1 its possible to follow K1 rules "kontantmetoden" or "fakturametoden" 
        and choose between simplified or usual year end. However, using the sales-module also
        implements accounts receivable and a sales ledger that implies "fakturametoden". 
        BAS 2015 K1 whould be sufficient for most K2 companies too. K2-sized companies can 
        still use traditional rules or choose to strictly follow K2-rules for the time being.
        
        Partners have an additional Company Registry (Organisationsnummer) derived from 
        TIN (momsregistreringsnumret).
        
        There are som documents (in Swedish) describing archiving, how to handle EDI-invoices,
        scanning of purchase invoices, basic accounting and numbering of account vouches attached
        to the module, static/doc-directory.
        
        You find the workplace for this module here https://launchpad.net/openerp-vertel
        Use Bugs or Answers funtions or contact anders.wallenquist@vertel.se directly if
        you have any questions or ideas.
    
     """,
    'author': 'Vertel',
    'website': 'http://www.vertel.se',
    'depends': ['account', 'base_vat', 'account_chart', 'l10n_multilang'],
    'init_xml': [],
    'update_xml': [
#        'data/account.account.type.csv',
        'data/account.chart.template.csv',
        'data/account.tax.template.csv',
        'data/account.account.template-before.csv',
        'data/account.account.template.csv',
        'data/account.account.template-k2.csv',
        'data/account.tax.code.template.csv',
        'data/account.tax.template-after.csv',
        'data/account.chart.template-after.csv',
        'data/res.partner.bank.type.csv',
#        'data/archive.faq.csv',
#        'l10n_se_wizard.xml',
        'account_report.xml',
        'account_vat_view.xml',
        'res_partner_view.xml',
#        'setup_view.xml',
    ],
#    'demo_xml' : [
#        'demo/demo.xml'
#    ],
    'installable': 'True',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
