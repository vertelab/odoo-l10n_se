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

    def make_sie(self, ver_ids):
        _logger.warning("make_sie"*100)
        def get_fiscalyears(ver_ids):
            year_list = set()
            for ver in ver_ids:
                year_list.add(ver.period_id.fiscalyear_id)
            return year_list
        def get_accounts(ver_ids):
            return list(set(ver_ids.mapped('line_ids.account_id')))

        if len(self) > 0:
            sie_form = self[0]
        if len(ver_ids) == 0:
            raise Warning('There are no entries for this selection, please do another')
        company = ver_ids[0].company_id
        fiscalyear = ver_ids[0].period_id.fiscalyear_id
        user = self.env['res.users'].browse(self._context['uid'])
        #if not company.company_registry:
        #    raise Warning("Please configure company registry!")
        str = ''
        str += '#FLAGGA 0\n'
        str += '#PROGRAM "Odoo" %s\n' % odoo.service.common.exp_version()['server_serie']
        str += '#FORMAT PC8\n' # ,Anger vilken teckenuppsattning som anvants
        # ~ str += '#GEN %s\n'% fields.Date.today().replace('-','')
        str += '#GEN %s\n'%  fields.Date.today().strftime("%Y%m%d")
        str += '#SIETYP 4\n'
        for fiscalyear in get_fiscalyears(ver_ids):
            # ~ str += '#RAR %s %s %s\n' %(self._get_rar_code(fiscalyear), fiscalyear.date_start.replace('-',''), fiscalyear.date_stop.replace('-',''))
            str += '#RAR %s %s %s\n' %(self._get_rar_code(fiscalyear), fiscalyear.date_start.strftime("%Y%m%d"), fiscalyear.date_stop.strftime("%Y%m%d"))
        str += '#FNAMN "%s"\n' %company.name
        str += '#ORGNR %s\n' %company.company_registry
        str += '#ADRESS "%s" "%s" "%s %s" "%s"\n' %(user.display_name, company.street, company.zip, company.city, company.phone)
        str += '#KPTYP %s\n' %(company.kptyp if company.kptyp else 'BAS2015')
        for account in get_accounts(ver_ids):
            str += '#KONTO %s "%s"\n' % (account.code, account.name)
            
        missing_sru_fields = []
        for account in get_accounts(ver_ids):
            if not account.sru_codes:
                missing_sru_fields.append(int(account.code))
                #_logger.warning('#SRU %s "%s"\n' % (account.code, account.sru_code))
            else:
                for sru_code in account.sru_codes:
                    str += '#SRU %s %s\n' % (account.code, sru_code.sru_code)
        if len(missing_sru_fields)>0:
            raise Warning(f'The accounts {missing_sru_fields} are missing an SRU code, add them before trying to export again.')
        #raise Warning("str: %s %s search:%s" % (str, self.env['account.move.line'].search(search),search))

        #TRANS  kontonr {objektlista} belopp  transdat transtext  kvantitet   sign
        #VER    serie vernr verdatum vertext regdatum sign
        # We seem to not add a regdatum which some parser don't agree with since we add the sign field
        # ~ _logger.warning("BEFORE GOING TROUGH ALL VER")
        ub = {}
        ub_accounts = []
        for ver in ver_ids:
            # ~ _logger.warning(f"{ver=}")
            if ver.period_id.special == False:
                str += '#VER %s "%s" %s "%s" %s %s\n{\n' % (self.escape_sie_string(ver.journal_id.type), ver.id, self.escape_sie_string(ver.date.strftime("%Y%m%d")), self.escape_sie_string(self.fix_empty(ver.narration))[:20], self.escape_sie_string(ver.create_date.strftime("%Y%m%d")),self.escape_sie_string(ver.create_uid.login))
                # ~ str += '#VER %s "%s" %s "%s" %s\n{\n' % (self.escape_sie_string(ver.journal_id.type), ver.id, self.escape_sie_string(ver.date.strftime("%Y%m%d")), self.escape_sie_string(self.fix_empty(ver.narration))[:20], self.escape_sie_string(ver.create_uid.login))
                #~ str += '#VER %s "%s" %s "%s" %s\n{\n' % (self.escape_sie_string(ver.journal_id.type), self.escape_sie_string('' if ver.name == '/' else ver.name), self.escape_sie_string(ver.date.replace('-','')), self.escape_sie_string(self.fix_empty(ver.narration)), self.escape_sie_string(ver.create_uid.login))
                #~ str += '#VER "" %s %s "%s" %s %s\n{\n' % (ver.name, ver.date, ver.narration, ver.create_date, ver.create_uid.login)
                for trans in ver.line_ids:
                    # ~ _logger.warning(f"jakmar: {trans.display_type}")
                    if trans.display_type == "line_note" or trans.display_type == 'line_section':
                        continue
                    str += '#TRANS %s {} %s %s "%s" %s %s\n' % (self.escape_sie_string(trans.account_id.code), trans.debit - trans.credit, self.escape_sie_string(trans.date.strftime("%Y%m%d")), self.escape_sie_string(self.fix_empty(trans.name)), trans.quantity, self.escape_sie_string(trans.create_uid.login))
                    if trans.account_id.code not in ub:
                        ub[trans.account_id.code] = 0.0
                    ub[trans.account_id.code] += trans.debit - trans.credit
                str += '}\n'
            else:  #IB
                for trans in ver.line_ids:
                    #_logger.warning(f"{trans=}")
                    str += '#IB %s %s %s\n' % (self._get_rar_code(fiscalyear), self.escape_sie_string(trans.account_id.code), trans.debit - trans.credit)
                    ub_accounts.append(trans.account_id.code)
        for account in ub:
            if account in ub_accounts:
                str += '#UB %s %s %s\n' % (self._get_rar_code(fiscalyear), self.escape_sie_string(account), ub.get(account, 0.0))
            else:
                #TODO: account.code can contain whitespace and should be handled as such here and elsewhere.
                #account.user_type.report_type in ('income', 'expense') => resultatkonto
                #account.user_type.report_type in ('assets', 'liability') => balanskonto
                str += '#RES %s %s %s\n' % (self._get_rar_code(fiscalyear), self.escape_sie_string(account), ub.get(account, 0.0))

        return str.encode('cp437','xmlcharrefreplace') # ignore
