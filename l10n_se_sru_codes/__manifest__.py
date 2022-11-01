# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2019 GRIMMETTE,LLC <info@grimmette.com>

{
    'name': 'SRU Sie export',
    'version': '14.0.0.1.0',
    'category': 'Extra Tools',
    'summary': 'Adds a SRU field for sie export',
    "license": "OPL-1",
    'description': """
        
    """,
    'depends': ['account','l10n_se_sie'],
    'data': [
        "security/ir.model.access.csv",
        "views/account.xml",
        "data/sru_account.xml",
        "data/server_actions.xml",
        
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}
