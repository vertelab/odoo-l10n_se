# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, RedirectWarning
from odoo import http
import base64
from datetime import datetime
import odoo

import logging
_logger = logging.getLogger(__name__)
class account_sie(models.TransientModel):
    _inherit = 'account.sie'

    def make_sie(self, ver_ids, ib_dict):
        def get_fiscalyears(ver_ids):
            year_list = set()
            for ver in ver_ids:
                year_list.add(ver.period_id.fiscalyear_id)
            return year_list


        def get_accounts_ver(ver_ids):
            return ver_ids.mapped('line_ids.account_id')
            
        def get_accounts_ib(ib_dict):
           ib_dict_accounts = []
           if ib_dict:
                for line in ib_dict:
                    ib_dict_accounts.append(line['account_code'])
                ib_dict_accounts = set(ib_dict_accounts)
                ib_dict_accounts_records = self.env['account.account']
                for line in ib_dict_accounts:
                    ib_dict_accounts_records += self.env['account.account'].search([('code','=',line)])
                return ib_dict_accounts_records   
                
                
        def get_accounts(ver_ids, ib_dict):
            if ver_ids and ib_dict:
                return list(set(get_accounts_ver(ver_ids) | get_accounts_ib(ib_dict)))
            if ver_ids:
               return list(set(get_accounts_ver(ver_ids)))
            if ib_dict:
               return list(set(get_accounts_ib(ib_dict)))
            return []

        if len(self) > 0:
            sie_form = self[0]
        company = self.env.company
        if ver_ids:
            fiscalyear = ver_ids[0].period_id.fiscalyear_id
        else:
            self.current_transaction_year
        user = self.env['res.users'].browse(self._context['uid'])

        str = ''
        str += '#FLAGGA 0\n'
        str += '#PROGRAM "Odoo" %s\n' % odoo.service.common.exp_version()['server_serie']
        str += '#FORMAT PC8\n'  # ,Anger vilken teckenuppsattning som anvants
        str += '#GEN %s\n' % fields.Date.today().strftime("%Y%m%d")
        str += '#SIETYP 4\n'
        for fiscalyear in get_fiscalyears(ver_ids):
            str += '#RAR %s %s %s\n' % (self._get_rar_code(fiscalyear), fiscalyear.date_start.strftime("%Y%m%d"),
                                        fiscalyear.date_stop.strftime("%Y%m%d"))
        str += '#FNAMN "%s"\n' % company.name
        str += '#ORGNR %s\n' % company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' % (
        user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' % (company.kptyp if company.kptyp else 'BAS2015')
        
        for account in get_accounts(ver_ids,ib_dict):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)
        
        missing_sru_fields = []
        for account in get_accounts(ver_ids,ib_dict):
            if not account.sru_codes:
                missing_sru_fields.append(int(account.code))
                #_logger.warning('#SRU %s "%s"\n' % (account.code, account.sru_code))
            else:
                for sru_code in account.sru_codes:
                    str += '#SRU %s %s\n' % (account.code, sru_code.sru_code)
        if len(missing_sru_fields)>0:
            raise Warning(f'The accounts {missing_sru_fields} are missing an SRU code, add them before trying to export again.')
        
        ub = {}
        ub_accounts = []
        for ver in ver_ids:
            # ~ _logger.warning(f"{ver=}")
            if ver.period_id.special == False:
                str += '#VER %s "%s" %s "%s" %s %s\n{\n' % (self.escape_sie_string(ver.journal_id.type), ver.id,
                                                            self.escape_sie_string(ver.date.strftime("%Y%m%d")),
                                                            self.escape_sie_string(self.fix_empty(ver.narration))[:20],
                                                            self.escape_sie_string(ver.create_date.strftime("%Y%m%d")),
                                                            self.escape_sie_string(ver.create_uid.login))
                for trans in ver.line_ids:
                    if trans.display_type == "line_note" or trans.display_type == 'line_section':
                        continue
                    str += '#TRANS %s {} %s %s "%s" %s %s\n' % (
                    self.escape_sie_string(trans.account_id.code), trans.debit - trans.credit,
                    self.escape_sie_string(trans.date.strftime("%Y%m%d")),
                    self.escape_sie_string(self.fix_empty(trans.name)), trans.quantity,
                    self.escape_sie_string(trans.create_uid.login))
                    if trans.account_id.code not in ub:
                        ub[trans.account_id.code] = 0.0
                    ub[trans.account_id.code] += trans.debit - trans.credit
                str += '}\n'
                
        for ib_val in ib_dict: #{'yearnr': -1, 'account_code': '1079', 'balance': 5000.0}, # IB
                    str += '#IB %s %s %s\n' % (
                    ib_val['yearnr'], ib_val['account_code'],
                    ib_val['balance'])
                    _logger.warning('#IB %s %s %s\n' % (
                    ib_val['yearnr'], ib_val['account_code'],
                    ib_val['balance']))
        #TODO #RES OCH #UB Borde vara för nyvarande 

        return str.encode('cp437', 'xmlcharrefreplace')  # ignore
