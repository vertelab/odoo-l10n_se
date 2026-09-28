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
    'version': '18.0.1.0.1',
    # Version ledger: 16.0 = Odoo version. 1 = Major. Non regressionable code. 2 = Minor. New features that are regressionable. 3 = Bug fixes
    'summary': 'Sweden - Chart of accounts.',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Vertel Sverige AB',
    'website': 'https://vertel.se/apps/odoo-l10n_se/l10n_se_extended',
    'license': 'AGPL-3',
    'contributor': '',
    'maintainer': 'Vertel AB',
    'repository': 'https://github.com/vertelab/odoo-l10n_se',
    'images': ['static/description/banner.png'],  # 560x280 px.
    'description': '''
Sweden - Accounting
===================

    BAS 2017 K1 and BAS 2017 in original can be found at www.bas.se.
            When you creats your companies, don't forget to change currency to SEK.
            Usually you want tax-code MP1 and I for standard sales and purchases,
            MP2, MP3 and I12/I6 are for products and services with 12 % and 6 % tax.
            You also may want to change the automatic created bank accounts to what
            accounts you want to associate them to.

    BFN (Bokföringsnämden) are working with accounting regulations for unlisted
            SME-companies in Sweden. The basis are K3, K1 and K2 are derived from K3 with
            a numerous of simplifications.

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

    Features:

        - Guided Wizards: Step-by-step dialogs for data entry.
        - UI Integration: Extends 1 view(s) in the Odoo interface.
        - Extends Odoo: Builds on account.chart.template, account.tax.
    ''',
    'depends': ['account', 'l10n_se'],
    'init_xml': [],
    'data': [
        # 'data/template/account.tax.group-se.csv',
        # 'data/template/account.tax-se.csv',
        # 'data/l10n_se_account_chart_template.xml',
        # 'data/account_chart_template_k23.xml',
        # 'data/account_tax_data.xml',
        # 'data/account_account_template_wt_tax_data.xml',
        # 'data/fiscal_position_data.xml',
        # 'data/l10n_se_account_chart_post_data.xml',
        # 'data/account_tax_template_hr_data.xml',
        'data/custom_address_formats.xml',
        # 'data/tax_partner.xml',
        # 'wizard/merge_chart_wizard.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',

    ],
    #'demo': [
        #'demo/load_account_chart_template_data.xml',
        #'demo/l10n_se_demo.xml',
    #],
    'installable': 'True',
    'application': 'False',
    'auto_install': True
}
