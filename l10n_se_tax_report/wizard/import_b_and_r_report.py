# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2018 Vertel AB (<http://vertel.se>).
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
from odoo import models, fields, api, _
from odoo.exceptions import except_orm, Warning, RedirectWarning
from tempfile import TemporaryFile
import base64
import sys
import traceback
try:
    from xlrd import open_workbook
except ImportError:
    _logger.info('project_task_planned_vehicle_import requires xlrd (pip install xlrd)')

import logging
_logger = logging.getLogger(__name__)

class ImportBalanceAndResultReports(models.TransientModel):
    _name = 'account.financial.report.balance_result.import'

    data = fields.Binary('File', required=True)
    message = fields.Text(string='Message', readonly=True)

    @api.multi
    def send_form(self):
        def parse_domain(dl):
            """Parse a list representing a BAS string."""
            #~ print '0 %s' % dl
            if not dl:
                return []
            changed = True
            while changed:
                changed = False
                for i in range(0, len(dl)):
                    if dl[i] == '(':
                        for j in range(i + 1, len(dl)):
                            if dl[j] == ')':
                                dl = dl[:i] + [parse_domain(dl[i + 1 : j])] + dl[j + 1:]
                                changed = True
                                break
                        break
            #~ print '1 %s' % dl
            #Handle spans (189x - 1930). Can contain wildcards for some mysterious reason.
            changed = True
            while changed:
                _logger.debug(dl)
                changed = False
                for i in range(0, len(dl)):
                    if dl[i] == '-':
                        dl = dl[:i - 1] + [[str(x) for x in range(int(dl[i - 1].replace('x', '0')), int(dl[i + 1].replace('x', '9')) + 1)]] + dl[i + 2:]
                        changed = True
                        break
            #~ print '2 %s' % dl
            # Handle numbers, wildcards and commas
            for i in range(0, len(dl)):
                if isinstance(dl[i], list) or dl[i] == '!':
                    pass
                    #~ print '2.0 %s' % dl
                elif dl[i] == ',':
                    dl[i] = []
                    #~ print '2.1 %s' % dl
                elif dl[i].isdigit():
                    dl[i] = [dl[i]]
                    #~ print '2.2 %s' % dl
                else:
                    _logger.debug(dl[i])
                    dl[i] = [str(x) for x in range(int(dl[i].replace('x', '0')), int(dl[i].replace('x', '9')) + 1)]
                    #~ print '2.3 %s' % dl
            #~ print '3 %s' % dl
            # Handle not
            ignore_ids = []
            changed = True
            while changed:
                changed = False
                for i in range(0, len(dl)):
                    if dl[i] == '!':
                        ignore_ids += dl.pop(i + 1)
                        dl.pop(i)
                        changed = True
                        break
            #~ print '4 %s' % dl
            # Build id list
            ids = []
            for e in dl:
                for id in e:
                    if id not in ignore_ids:
                        ids.append(id)
            return ids

        def get_domain(text):
            """Get a domain from a BAS string."""
            _logger.debug('|%s|' % text)
            try:
                if isinstance(text, float):
                    return None, [('code', '=', str(int(text)))], None
                txt = text.replace(' ', '')
                txt = txt.replace(u'`', '')
                txt = txt.replace(u'–', '-')
                if txt[0] in ('+', '-'):
                    sign = txt[0]
                    txt = txt[1:]
                else:
                    sign = None
                txt = txt.replace('exkl.', '!').replace('samt', ',').replace('och', ',')
                separators = ',-()!'
                for sep in separators:
                    txt = txt.replace(sep, ' %s ' % sep)
                return sign, [('code', 'in', parse_domain(txt.split()))], None
            except:
                error_info = sys.exc_info()
                _logger.warn('\n' + ''.join(traceback.format_exception(error_info[0], error_info[1], error_info[2])))
                return None, [], "Couldn't parse domain: %s" % text
        errors = []
        res = []
        year = ''
        name = ''
        with TemporaryFile('w+') as fileobj:
            fileobj.write(base64.decodestring(self.data))
            fileobj.seek(0)
            wb = open_workbook(file_contents=fileobj.read(), formatting_info=True)
            ws = wb.sheet_by_index(0)
            heading = None
            account = None
            state = 0
            year = str(int(ws.cell(0, 0).value))
            name = ws.cell(0, 2).value
            for row in ws.get_rows():
                #~ print row
                if state == 0:
                    #Looking for start of accounts list
                    if row and row[0].value == u'Fält-kod':
                        state = 1
                elif state == 1:
                    # Looking for new heading or account to process
                    if len(row) > 3 and row[3].value:
                        #Found an account row.
                        if row[1].value:
                            #This row has an SRU code.
                            sign, domain, error = get_domain(row[3].value)
                            if error:
                                errors.append(error)
                            account = {
                                'code': row[1].value,
                                'name': row[2].value,
                                'domains': [domain],
                                'field_codes': [{
                                    'code': int(row[0].value) if row[0].value != '' else '',
                                    'sign': sign,
                                    'domain': domain,
                                }]
                            }
                            heading['accounts'].append(account)
                        else:
                            #No SRU code on this row. Shares SRU with previous row.
                            sign, domain, error = get_domain(row[3].value)
                            if error:
                                errors.append(error)
                            if row[0].value:
                                account['field_codes'].append({
                                    'code': int(row[0].value) if row[0].value != '' else '',
                                    'sign': sign,
                                    'domain': domain,
                                })
                            account['domains'].append(domain)
                    elif len(row) > 2 and row[2].value and row[2].value.isupper():
                        #Top level heading
                        heading = {
                            'name': row[2].value,
                            'accounts': [],
                            'children': [],
                            'height': wb.font_list[wb.xf_list[row[2].xf_index].font_index].height,
                            'parent': None,
                        }
                        res.append(heading)
                    elif len(row) > 2 and row[2].value:
                        #Subheading
                        h = heading
                        height = wb.font_list[wb.xf_list[row[2].xf_index].font_index].height
                        #~ print height
                        while True:
                            #~ print 'h: %s' % h['name']
                            if not h['parent']:
                                break
                            if h['height'] > height:
                                break
                            h = h['parent']
                        heading = {
                            'name': row[2].value,
                            'accounts': [],
                            'children': [],
                            'height': height,
                            'parent': h,
                        }
                        h['children'].append(heading)

        def create_account(values, parent, sequence):
            _logger.debug(values)
            accounts = self.env['account.account'].browse()
            for domain in values['domains']:
                accounts |= self.env['account.account'].search(domain)
            vals = {
                'name': '%s %s' % (values['code'], values['name']),
                'parent_id': parent.id,
                'type': 'accounts',
                'sequence': sequence,
                'sign': 1,
                'sru': values['code'],
                'display_detail': 'no_detail',
                'account_ids': [(6, 0, [a.id for a in accounts])],
            }
            for code in values['field_codes']:
                if not code['sign'] or code['sign'] == '+':
                    vals['field_code'] = code['code']
                elif code['sign'] == '-':
                    vals['field_code_neg'] = code['code']
            account = self.env['account.financial.report'].create(vals)

        def create_heading(values, parent, sequence):
            heading = self.env['account.financial.report'].create({
                'name': values['name'],
                'parent_id': parent.id,
                'type': 'sum',
                'sequence': sequence,
                'sign': 1,
            })
            i = 0
            for child in values['children']:
                create_heading(child, heading, i)
                i += 1
            for account in values['accounts']:
                create_account(account, heading, i)
                i += 1
        report = self.env['account.financial.report'].create({
            'name': '%s - %s' % (name, year),
            'type': 'sum',
            'sequence': 0,
            'sign': 1,
        })
        i = 0
        for values in res:
            create_heading(values, report, i)
            i += 1
        self.env['ir.filters'].create({
            'name': '%s - %s' % (name, year),
            'user_id': False,
            'model_id': 'account.financial.report',
            'domain': [('id', 'child_of', report.id)],
        })
        if not errors:
            self.message = "Import successfull!"
        else:
            message = "Errors when importing!"
            for e in errors:
                message += '\n' + e
            self.message = message
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.financial.report.balance_result.import',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
