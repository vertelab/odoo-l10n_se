# -*- coding: utf-8 -*-
##############################################################################
#
#
#
##############################################################################


{
    'name': 'l10n_se_report',
    'version': '1.0',
    'category': 'other',
    'summary': 'Reports for l10n_se project',
    'author': 'Vertel AB',
    'website': 'http://www.vertel.se',
    'depends': ['base'],
    'data': [ 'l10n_se_report_view.xml',
              'daily_ledger.xml',
              'basic_r_and_b_view.xml',
              'create_year_end_report.xml'],

    'installable': True,
    'application': False,
    #'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
