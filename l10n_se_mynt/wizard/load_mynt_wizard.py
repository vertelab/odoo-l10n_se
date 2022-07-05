# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Enterprise Management Solution, third party addon
#    Copyright (C) 2017 Vertel AB (<http://vertel.se>).
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
from odoo import api, fields, models, _
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning
from odoo.exceptions import ValidationError,UserError
import zipfile
import base64
import tempfile
from io import BytesIO
import csv
from zipfile import BadZipfile

import logging
_logger = logging.getLogger(__name__)
logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_bgmax method to account.bank.statement.import."""
    _inherit = 'account.statement.import'

    @api.model
    def _parse_file(self, statement_file):
        """Parse a Mynt zip file."""
        try:
            _logger.warning(u"Try parsing with Mynt.")
            return self.extract_zip(statement_file)
        except BadZipfile as e:
            _logger.warning("Was not a zip file.")
            return super(AccountBankStatementImport, self)._parse_file(statement_file)
        except ValueError as e:
            _logger.warning("Was a zip file but not a Mynt zip file.")
            return super(AccountBankStatementImport, self)._parse_file(statement_file)
            
            
    def extract_zip(self,statement_file):
        account_card_statement_id = False
        statement_file_copy = statement_file
        file_data = base64.b64decode(self.statement_file)
        with zipfile.ZipFile(BytesIO(file_data)) as data:
            filenames_csv = [filename for filename in data.namelist() if filename.endswith('.csv')]  # A list of filenames that end with .csv, this is used since i don't know what the csv file is called or if there are several of them.
            # ~ _logger.warning(f"{data.namelist()}")
            if not filenames_csv:
                raise ValueError("For Mynt Zip File,There is no content in the zipped file.")
            for filename in filenames_csv:
                data_read = data.read(filename) # Is a byte string now with "\r\n" in it.
                data_read = data_read.decode("utf-8").split("\r\n") #Seem to have to make into regular string and make a list split on "\r\n" for the csv parser to work
                csv_reader = csv.DictReader(data_read)
                first_row = next(csv.DictReader(data_read))
                _logger.warning(f"{first_row}")
                 #checking all keys exist in dictionary
                # Column names are Date, Account, Amount, Currency, Original amount, Original currency, VAT amount, VAT rate, Description, Category, Comment, Filename, Settlement status, Person, Card number, Accounting status, Cost center, Project
                expected_mynt_keys = ('Date', 'Amount', 'Currency', 'Original amount', 'Original currency', 'VAT amount', 'VAT rate', 'Reverse VAT', 'Description', 'Account', 'Category', 'Comment', 'Filename', 'Settlement status', 'Person', 'Team', 'Card number', 'Card name', 'Accounting status')
                _logger.warning(f"{first_row.keys()}")
                if set(expected_mynt_keys).issubset(first_row.keys()):
                    _logger.warning(("given all keys are present in the dictionary. This seems to be a mynt csv file.")) 
                else: 
                    _logger.warning(_("given all keys are not present in the dictionary. This is not a mynt csv file.")) 
                    raise ValueError(_("given all keys are not present in the dictionary. This is not a mynt csv file."))
                
                #This far we have a zip file which contains a csv file that follows the mynt format. So we can now check to see if the Journal is configured for mynt import.
                journal_id = self.env['account.journal'].browse(self.env.context.get('journal_id', False))
                _logger.warning(f"{journal_id=}")
                if not journal_id.type == "card":
                    raise Warning(_("For Mynt Zip File, please select a Card journal"))
                if not journal_id.card_debit_account:
                    raise Warning(_("For Mynt Zip Files, please select a card debit account on the selected Journal"))
                if not journal_id.card_credit_account:
                    raise Warning(_("For Mynt Zip Files, please select a card credit account on the selected Journal"))
                    
                total_amount = 0
                reverse_move_date = ""
                row1 = next(csv_reader) 
                card_statement_date = datetime.strptime(row1.get("Date"), '%Y-%m-%d').replace(day = 1)
                card_statement_date_char = datetime.strftime(card_statement_date,'%Y:%m')
                account_card_statement_id = self.env["account.card.statement"].create({'date':card_statement_date,'name':_('mynt card transaction: %s') % card_statement_date_char})
                for row in csv_reader:
                    if row.get('Amount') == '':
                        row['Amount'] = '0'
                    if row.get('Original amount') == '':
                        row['Original amount'] = '0'
                    if row.get('VAT amount') == '':
                        row['VAT amount'] = '0'
                    
                    if float(row["Amount"]) <= 0: #Is a debit transaction
                        reverse_move_date = datetime.strptime(row.get("Date"), '%Y-%m-%d')
                        account_move = self.create_account_move(row,"debit",journal_id)
                        self.create_account_card_statement_line(row,account_move,account_card_statement_id)
                        total_amount += account_move.amount_total
                    elif float(row["Amount"]) >= 0:#Is a credit transaction
                        account_move = self.create_account_move(row,"credit",journal_id)
                        self.create_account_card_statement_line(row,account_move,account_card_statement_id)
                        # ~ total_amount += account_move.amount_total
                     # ~ #Add Attachment
                    if row["Filename"] and row["Filename"] in data.namelist(): 
                        self.env['ir.attachment'].create({
                            'name': row["Filename"],
                            'type': 'binary',
                            'res_model': "account.move",
                            'res_id': account_move.id,
                            'datas': base64.b64encode(data.read(row["Filename"])),
                        })
                    else:
                        account_move.to_check = True# Missing an attechment, set 
                    # ~ raise ValidationError('You done')
                        
                        
                reverse_move_date = reverse_move_date.replace(day = 5) + relativedelta(months=1)
                reverse_move_period_id = self.env['account.period'].date2period(reverse_move_date).id
                card_credit_account = journal_id.card_credit_account
                card_debit_account = journal_id.card_debit_account
                
                #move_type used to be in_invoice
                # ~ payment_account_move = self.env['account.move'].with_context(check_move_validity=False).create({'journal_id': journal_id.id,"move_type":'entry',"ref": "Mynt Samling",'date':reverse_move_date,'invoice_date':reverse_move_date,'period_id':reverse_move_period_id})
                # ~ account_move_line = self.env['account.move.line'].with_context(check_move_validity=False)
                # ~ debit_line = account_move_line.create({
                    # ~ 'account_id': card_debit_account.id,
                    # ~ 'debit': total_amount,
                    # ~ 'exclude_from_invoice_tab': False,
                    # ~ 'move_id': payment_account_move.id,
                # ~ })
                # ~ credit_line = account_move_line.create({
                    # ~ 'account_id': card_credit_account.id,
                    # ~ 'credit': total_amount,
                    # ~ 'exclude_from_invoice_tab': True,
                    # ~ 'move_id': payment_account_move.id,
                # ~ })  
                # ~ payment_account_move.with_context(check_move_validity=False)._recompute_dynamic_lines()
                # ~ account_card_statement_id.account_move_id = payment_account_move.id
                account_card_statement_id.journal_id = journal_id
                self.env['ir.attachment'].create({
                                'name': self.statement_filename,
                                'type': 'binary',
                                'res_model':"account.card.statement",
                                'res_id': account_card_statement_id.id,
                                'datas':statement_file,
                            })
            return account_card_statement_id,"Mynt"
                
    def import_single_statement(self, single_statement_data, result):
        if single_statement_data[1] == "Mynt":
            result["statement_ids"] = single_statement_data
            result["notifications"] = "Mynt"
            return 
        return super(AccountBankStatementImport, self).import_single_statement(single_statement_data, result)
                
    
    def import_file_button(self):
        """Process the file chosen in the wizard, create bank statement(s)
        and return an action."""
        self.ensure_one()
        result = {
            "statement_ids": [],
            "notifications": [],
        }
        logger.info("Start to import bank statement file %s", self.statement_filename)
        file_data = base64.b64decode(self.statement_file)
        self.import_single_file(file_data, result)
        
        _logger.warning(f"import_file_button {result=}") ##################################################################
        if result['notifications'] == 'Mynt':
            return {
                'name': _('Card Transaction'),
                'view_id':self.env.ref("account_journal_card_type.account_card_statement_form").id,
                'res_id':result['statement_ids'][0].id,
                # ~ 'domain': domain,
                'res_model': 'account.card.statement',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
            }

        ##############################################################################################################
        
        logger.debug("result=%s", result)
        if not result["statement_ids"]:
            raise UserError(
                _(
                    "You have already imported this file, or this file "
                    "only contains already imported transactions."
                )
            )
        self.env["ir.attachment"].create(self._prepare_create_attachment(result))
        if self.env.context.get("return_regular_interface_action"):
            action = (
                self.env.ref("account.action_bank_statement_tree").sudo().read([])[0]
            )
            if len(result["statement_ids"]) == 1:
                action.update(
                    {
                        "view_mode": "form,tree",
                        "views": False,
                        "res_id": result["statement_ids"][0],
                    }
                )
            else:
                action["domain"] = [("id", "in", result["statement_ids"])]
        else:
            # dispatch to reconciliation interface
            lines = self.env["account.bank.statement.line"].search(
                [("statement_id", "in", result["statement_ids"])]
            )
            action = {
                "type": "ir.actions.client",
                "tag": "bank_statement_reconciliation_view",
                "context": {
                    "statement_line_ids": lines.ids,
                    "company_ids": self.env.user.company_ids.ids,
                    "notifications": result["notifications"],
                },
            }
        return action
                     
    def create_account_card_statement_line(self,row,account_move,account_card_statement_id):
        
            currency = self.env['res.currency'].search([('name','=ilike',row.get('Currency'))])
            if not currency:
                currency = self.env.ref('base.main_company').currency_id
                
            account = self.env['account.account'].search([('name','=',row.get('Account'))])
            
            if not account and float(row.get('Amount')) > 0:
            # ~ row.get('Description') == 'Credit Repayment': # ~ Kreditupplysning 6061
                account = self.env["account.account"].search([("code","=","6061")])
            elif not account:
                account = self.env["account.account"].search([("code","=","4001")])
            return self.env["account.card.statement.line"].create({
            'account_card_statement_id':account_card_statement_id.id,
            'account_move_id':account_move.id,
            'date':row.get('Date',"No value found"), 
            'amount':float(row.get('Amount',0)),
            'currency':currency.id,
            'original_amount':float(row.get('Original amount',0)),
            'original_currency':row.get('Original currency',"No value found"),
            'vat_amount':float(row.get('VAT amount',0)),
            'vat_rate':row.get('VAT rate',"No value found"),
            'reverse_vat':row.get('Reverse VAT',"No value found"), 
            'description':row.get('Description',"No value found"),
            'account':account.id,
            'category':row.get('Category',"No value found"),
            'comment':row.get('Comment',"No value found"),
            'filename':row.get('Filename',"No value found"),
            'settlement_status':row.get('Settlement status',"No value found"),
            'person':row.get('Person',"No value found"),
            'team':row.get('Team',"No value found"),
            'card_number':row.get('Card number',"No value found"),
            'card_name':row.get('Card name',"No value found"),
            'accounting_status':row.get('Accouning status',"No value found"), 
            })
    
    def create_account_move(self, row, credit_or_debit, journal_id):
        amount = float(row["Amount"])  * (-1.0)
        to_check = False
        if row.get("VAT amount","") == "":
           row["VAT amount"] = "0.0" 
        tax_amount = float(row.get("VAT amount")) * (-1.0)
        amount_without_tax = amount - tax_amount
        
        if row.get("VAT rate") == "" and float(row.get('Amount')) > 0:
           row["VAT rate"]  = "0.0" 
           to_check = True
        vat_rate = float(row.get("VAT rate").replace("%",""))
        _logger.warning(f"{vat_rate=}")
        if vat_rate == 0.0:
            tax_account = False
        elif vat_rate == 6:
            tax_account = self.env["account.tax"].search([("name","=","I6"),("amount","=","6")])
        elif vat_rate == 12:
            tax_account = self.env["account.tax"].search([("name","=","I12"),("amount","=","12")])
        elif vat_rate == 25:
            tax_account = self.env["account.tax"].search([("name","=","I"),("amount","=","25")])
        else: # Default to 25% seems like the safest way of handling weird input data, maybe the should throw an error, since 0%,6%,12% and 25% vat are the only valid ones here in sweden.
            to_check = True
            tax_account = self.env["account.tax"].search([("name","=","I")])
        if not tax_account and not vat_rate == 0.0:
            raise ValidationError(f"No valid tax account found, for vat rate {vat_rate}")
                 
        account = self.env["account.account"].search([("code","=",row.get("Account"))])
        if not account and float(row.get('Amount')) > 0:
            # ~ row.get('Description') == 'Credit Repayment': # ~ Kreditupplysning 6061
            account = self.env["account.account"].search([("code","=","6061")])
        elif not account:
            account = self.env["account.account"].search([("code","=","4001")])
            to_check = True
        
        partner_id = False
        if row.get('Description'):
            partner_id = self.env['res.partner'].search([('name','=',row.get('Description'))],limit=1)
            if not partner_id:
                partner_id = self.env['res.partner'].create({'name':row.get('Description'),'company_type':'company'})
        else:
            to_check = True
            
        
        if "@" in row.get("Comment") :
            _logger.warning("FOUND @ IN COMMENT" *100)
            to_check = True
        
        #Some lines are a Credit Repayment, and are postivte. These are not receipts
        # ~ move_type = "in_receipt"
        # ~ if float(row.get('Amount')) > 0:
            # ~ move_type = "entry"
        move_type = "in_receipt"
            
        period_id = self.env['account.period'].date2period(datetime.strptime(row.get("Date"), '%Y-%m-%d'))
        account_move = self.env['account.move'].with_context(check_move_validity=False).create({
            'partner_id':partner_id,
            'journal_id': journal_id.id,
            "move_type":move_type,
            'ref':row.get("Comment"),
            'invoice_origin':row.get("Person","") + " " + row.get("Card name","") + " " + row.get("Card number",""),
            'period_id':period_id.id,
            'date':row.get("Date"),
            'invoice_date':row.get("Date"),
            'to_check':to_check
        })
        
        account_move_line = self.env['account.move.line'].with_context(check_move_validity=False)
        credit_amount = 0
        debit_amount = 0
        if credit_or_debit == 'credit':
            credit_amount = -amount_without_tax
        else:
            debit_amount = amount_without_tax 
            
        if tax_account:
            tax_account = [(6, 0, [tax_account.id])]
        move_line = account_move_line.create({
            'account_id': account.id,
            'credit': credit_amount,
            'debit': debit_amount,
            'exclude_from_invoice_tab': False,
            'move_id': account_move.id,
            'name': row.get("Category","")+" "+row.get("Comment",""),
            'tax_ids':tax_account,
        })
        move_line._onchange_mark_recompute_taxes()
        account_move.with_context(check_move_validity=False)._recompute_dynamic_lines()
        return account_move
        
   
