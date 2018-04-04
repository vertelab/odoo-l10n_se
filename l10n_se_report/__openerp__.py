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
    'license': 'AGPL-3',
    'website': 'http://www.vertel.se',
    'depends': ['l10n_se', 'report_glabels'],
    'data': [
        'l10n_se_report_view.xml',
        'daily_ledger.xml',
        'basic_r_and_b_view.xml',
        'create_year_end_report.xml',
        'wizard/agd_report.xml',
        'wizard/moms_report.xml',
        'wizard/year_end_report.xml',
        'wizard/glabel_report.xml',
        'res_config_view.xml',
    ],

    'installable': True,
    'application': False,
    #'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
