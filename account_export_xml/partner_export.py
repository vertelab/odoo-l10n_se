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


for m in odoo.env['ir.model'].browse(odoo.env['ir.model'].search([])):
    #print m.model,"(%s non persistant %s)" % (m.name,m.osv_memory)
    if not (m.osv_memory or m.model[0:7] == 'ir.qweb' or m.model[0:7] == 'report.' or m.model[0:12] == 'website.qweb' or m.model in ['website_qweb','company.share.setting','crm.tracking.mixin','edi.edi','ir.http','ir.model','ir.needaction_mixin','mail.thread','publisher_warranty.contract','report.abstract_report','report.account.report_agedpartnerbalance','report.account.report_analyticbalance']): 
        fields = [item[0].encode('utf-8') for item in odoo.env[m.model].browse([]).fields_get().items()]
        if fields and m.model != 'board.board' and (not m.model in ['calendar.alarm_manager','company.share.setting','_unknown','website_qweb']) and odoo.env[m.model].search_count([]) > 0:
            #print m.model,fields
            #'share_capital_amount','share_blocks_amount',shareholder
            #f=['share_capital_amount','sale_note', 'rml_footer', 'create_date', 'rml_header', 'share_capital','id', 'rml_paper_format', 'security_lead',   'timesheet_max_difference', 'currency_id', 'internal_transit_location_id', 'logo_web', 'po_lead', 'authorised_share_capital', 'logo', 'font', 'partner_id', 'expects_chart_of_accounts', 'account_no', 'city',  'display_name', 'zip','__last_update', 'country_id', 'timesheet_range', 'expense_currency_exchange_account_id', 'id', 'parent_id', 'paperformat_id', 'rml_footer_readonly', 'email', 'vat', 'website', 'propagation_minimum_delta', 'fax', 'bank_ids', 'name', 'share_total', 'share_amount', 'street2', 'child_ids', 'custom_footer', 'phone', 'user_ids', 'rml_header2', 'rml_header3', 'write_date', 'rml_header1', 'vat_check_vies', 'write_uid', 'project_time_mode_id', 'create_uid', 'paypal_account', 'company_registry', 'overdue_msg', 'currency_ids', 'street', 'state_id', 'tax_calculation_rounding_method', 'income_currency_exchange_account_id', 'nominal_value']
            #for f2 in f:
            #    fields = [f2,'id']
            print "Dump",m.model
            with open('%s.csv' % m.model.replace('.','_'), 'w') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fields)
                writer.writeheader()
                for partner in odoo.env[m.model].read(odoo.env[m.model].search([]), fields):
                    for field in fields:
                        if isinstance(partner[field], basestring):
                            partner[field] = partner[field].encode('utf-8')
                        partner[field] = str(partner[field])
                    writer.writerow(partner)
        else:
            print "Empty: ", m.model
    else:
        print "Empty",m.model
