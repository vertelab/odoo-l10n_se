from odoo import models, fields, api, _
import logging
import base64
from lxml import etree
import json
import ast
_logger = logging.getLogger(__name__)


class AccountAccount(models.Model):
    _inherit = 'account.account'
    sru_codes = fields.Many2many('account.sru.code', 'sru_codes_account_account', 'op_sru_id', 'op_account_id', string='SRU Codes')
    
class AccountSRU(models.Model):
    
    _name = 'account.sru.code'
    _rec_name = 'sru_code'
    sru_code = fields.Char(string="SRU",help="SRU Code which will be used in an sie export")
    rad_ink_2 = fields.Char(string="Rad Ink 2",help="Rad Ink 2")
    accounts = fields.Many2many('account.account', 'sru_codes_account_account', 'op_account_id', 'op_sru_id', string='Accounts')
    text_intervall_original = fields.Char(string="Excel Original Text",help="Account Interval from the excel ark from bas.se.", readonly=True)
    text_intervall = fields.Char(string="Account Excel Interval",help="Account Interval from the excel ark from bas.se.")
    text_intervall_exclude = fields.Char(string="Account Excel Interval Exclude",help="Account Interval from the excel ark from bas.se.")
    text_intervall_formated = fields.Char(string="Account Odoo Domain",help="The odoo domain that selects accounts. Is based on Account Excel Interval.")
    text_intervall_formated_exclude = fields.Char(string="Account Odoo Exclude Domain",help="The odoo domain that unselects accounts. Is based on Account Excel Interval Exclude.")
    benamning = fields.Char(string="Benämning")
    notes = fields.Char(string="Notes", help="Notes about why some intervalls are chosen.")
    
    def use_accounts_domain(self):
        for record in self:
            account_ids = []
            if record.text_intervall_formated:
                domain_list = ast.literal_eval(record.text_intervall_formated)
                if record.text_intervall_formated_exclude:
                    domain_list = domain_list + ast.literal_eval(record.text_intervall_formated_exclude)
                    domain_list.insert(0, "&")
                _logger.warning(f"{domain_list}=")
                domain_list
                account_ids = self.env['account.account'].search(domain_list)
                _logger.warning(f"{account_ids=}")
                record.write({"accounts":[(6, 0, account_ids.ids)]})
            else:
                record.write({"accounts":[(6, 0, [])]})

    def set_accounts_domain(self):
        for record in self:
            record.set_accounts_domain_intervall()
            if record.text_intervall_exclude:
                record.set_accounts_domain_intervall_exclude()
            
    def set_accounts_domain_intervall(self):
        formated_domains_list = []
        ## This is horrible parsing and could be better, https://www.bas.se/kontoplaner/sru/ you're welcome to try.
        if not self.text_intervall:
            self.text_intervall_formated = False
            return
        domains = self.text_intervall.split(',')
        for domain in domains:
            if domain[0] == "–" or domain[0] == "-":
                break
            if '`' in domain:
                domain = domain.replace('`','')
            if '+' in domain:
                domain = domain.replace('+','')
            if '–' in domain:
                domain = domain.replace('–','-')
            if "-" in domain:
                to_from_domain = domain.split('-')
                from_account = to_from_domain[0]
                from_account = from_account.replace('x','0')
                to_account = to_from_domain[1]
                to_account = to_account.replace('x','9')
                range_domain = list(range(int(from_account), int(to_account)+1))
                formated_domain = [str(x) for x in range_domain]
                formated_domains_list = formated_domains_list + formated_domain
            elif "x" in domain:
                from_account = domain.replace('x','0')
                to_account = domain.replace('x','9')
                range_domain = list(range(int(from_account), int(to_account)+1))
                formated_domain = [str(x) for x in range_domain]
                formated_domains_list = formated_domains_list + formated_domain
            else:
                formated_domain = str(domain).strip()
                formated_domains_list = formated_domains_list + [formated_domain]
            
            
        self.text_intervall_formated = [('code','in',formated_domains_list)] 
        
    def set_accounts_domain_intervall_exclude(self):
        formated_domains_list = []
        ## This is horrible parsing and could be better, https://www.bas.se/kontoplaner/sru/ you're welcome to try.
        domains = self.text_intervall_exclude
        domains = domains.replace('`','')
        domains = domains.replace('och',',')
        domains = domains.replace('samt',',')
        domains = domains.replace('(','')
        domains = domains.replace(')','')
        domains = domains.replace('+','')
        domains = domains.replace('–','-')
        domains = domains.split(',')
        for domain in domains:
            if domain[0] == "–" or domain[0] == "-":
                break 
            if "-" in domain:
                to_from_domain = domain.split('-')
                from_account = to_from_domain[0]
                from_account = from_account.replace('x','0')
                to_account = to_from_domain[1]
                to_account = to_account.replace('x','9')
                range_domain = list(range(int(from_account), int(to_account)+1))
                formated_domain =  [str(x) for x in range_domain]
                formated_domains_list = formated_domains_list + formated_domain
            elif "x" in domain:#112x
                from_account = domain.replace('x','0')
                to_account = domain.replace('x','9')
                range_domain = list(range(int(from_account), int(to_account)+1))
                formated_domain = [str(x) for x in range_domain]
                formated_domains_list = formated_domains_list + formated_domain
            else:#7202
                formated_domain = str(domain).strip()
                formated_domains_list = formated_domains_list + [formated_domain]
            
        self.text_intervall_formated_exclude = [('code','not in',formated_domains_list)] 
            


