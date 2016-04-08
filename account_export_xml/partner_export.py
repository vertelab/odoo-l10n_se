#!/usr/bin/python
# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2016- Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#pip install odoorpc
# ~/.odoorpc
#[dermanord]
#host = localhost
#protocol = xmlrpc
#user = admin
#timeout = 120
#database = <database>
#passwd = <password>
#type = ODOO
#port = 8069

#pip install odoorpc
import csv

try:
    import odoorpc
except ImportError:
    raise Warning('odoorpc library missing, pip install odoorpc')

params = odoorpc.session.get('partner_export')
odoo = odoorpc.ODOO(params.get('host'),port=params.get('port'))

# Check available databases
#print(odoo.db.list())

# Login (the object returned is a browsable record)
#odoo.login(local_database,local_user, local_passwd)
odoo.login(params.get('database'),params.get('user'),params.get('passwd'))

fields = [item[0].encode('utf-8') for item in odoo.env['res.partner'].browse([]).fields_get().items()]


with open('partner_export.csv', 'w') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fields)
    writer.writeheader()
    for partner in odoo.env['res.partner'].read(odoo.env['res.partner'].search([]), fields):
        for field in fields:
            if isinstance(partner[field], basestring):
                partner[field] = partner[field].encode('utf-8')
            partner[field] = str(partner[field])
        writer.writerow(partner)
