# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo SA, Open Source Management Solution, third party addon
#    Copyright (C) 2021- Vertel AB (<https://vertel.se>).
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

{
    'name': 'l10n_se: Sweden - Accounting',
    'version': '14.0.0.1.0',
    # Version ledger: 14.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Sweden - Chart of accounts',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Vertel AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'images': ['static/description/banner.png'], # 560x280 px.
    'description': """
    Sweden - Chart of accounts

        * BAS 2021 K1 (Minimal chart of account, rules from SKV-283 v16)
        * BAS 2021 (K2-K4, follows INK2R-form and rules in SKV-294 v11)
        * Tax-codes from SKV-4700 r1-49  SKV-409

        BAS 2017 K1 and BAS 2017 in original can be found at www.bas.se.
        When you creats your companies, don't forget to change currency to SEK.
        Usually you want tax-code MP1 and I for standard sales and purchases,
        MP2, MP3 and I12/I6 are for products and services with 12 % and 6 % tax.
        You also may want to change the automatic created bank accounts to what
        accounts you want to associate them to.

        BFN (Bokföringsnämden) are working with accounting regulations for unlisted
        SME-companies in Sweden. The basis are K3, K1 and K2 are derived from K3 with
        a numerous of simplifications.

        * K1 are sole traders with a turnover under 3 MSEK and can use a simplified
          year end.
        * K2 are small companies and associations that doesn't pass more than one
          of three limits two years in a row: not more than 50 employees in average, assets
          worth more than 40 MSEK, not more than 80 MSEK in turnover.
        * K3 are an unlisted company that passes two or more of theese limits.
        * K4 are an enlisted public company.

        K1 and K2 are not obliged to use an external auditor (turn over under 80 MSEK), using
        BAS 2021 K1 its possible to follow K1 rules "kontantmetoden" or "fakturametoden"
        and choose between simplified or usual year end. However, using the sales-module also
        implements accounts receivable and a sales ledger that implies "fakturametoden".
        BAS 2017 K1 whould be sufficient for most K2 companies too. K2-sized companies can
        still use traditional rules or choose to strictly follow K2-rules for the time being.

        Partners have an additional Company Registry (Organisationsnummer) derived from
        TIN (momsregistreringsnumret).

        There are som documents (in Swedish) describing archiving, how to handle EDI-invoices,
        scanning of purchase invoices, basic accounting and numbering of account vouches attached
        to the module, static/doc-directory.

        You find the workplace for this module here https://launchpad.ne://github.com/vertelab/odoo-l10n_se
        Use Bugs or Answers funtions or contact support@vertel.se directly if
        you have any questions or ideas.
        
        Installation Instructions.
        Odoo SA already has a l10n_se module, and if you want to use this one you have remove core-odoo/addons/l10n_se and core-odoo/addons/l10n_se_ocr.
        After that step you should be able to install this module. 
        
        Next step is to choose a chart_of_accounts and that can be done in the settings meny but you need to check "Show Full Accounting Features" on you current user.
        

     """,
    'depends': ['account_period', 'base_vat', 'product', 'account', 'account_admin_rights'],
    'init_xml': [],
    'data': [
        'views/account_view.xml',
        'data/account_account_template_data.xml',
        'data/l10n_se_account_chart_template.xml',
        'data/account_account_type.xml',
        'data/account_chart_template_k23.xml',
        'data/account_tax_data.xml',
        'data/account_account_template_wt_tax_data.xml',
        'data/fiscal_position_data.xml',
        'data/l10n_se_account_chart_post_data.xml',
        'data/account_reconcile_model_data.xml',
        'data/account_tax_template_hr_data.xml',
        'data/set_account_type_on_account.xml',
        'security/ir.model.access.csv',
        #'data/load_account_chart_template_data.xml',

    ],
    'demo': [
        'demo/load_account_chart_template_data.xml',
        'demo/l10n_se_demo.xml',
    ],
    'installable': 'True',
    'application': 'False',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
