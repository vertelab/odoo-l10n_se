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
from odoo.exceptions import ValidationError
import zipfile
import base64
import tempfile
from io import BytesIO
import csv

import logging
_logger = logging.getLogger(__name__)


class LoadMynt(models.TransientModel):
    _name = 'load.mynt.wizard'
    _description = 'Mynt Import Wizard'
    
    mynt_directory = fields.Binary(string="Choose a file to import")
    journal_id = fields.Many2one('account.journal', string='Mynt Journal')
    
    def import_file(self):
        self.journal_id = self.env['account.journal'].browse(self.env.context.get('active_id', False))
        _logger.warning(f"{self.journal_id=}")
        if not self.journal_id:
            raise Warning(_("Please select a journal"))
        if not self.journal_id.is_card_journal:
            raise Warning(_("Please select a Card journal"))
        if not self.journal_id.card_debit_account:
            raise Warning(_("Please select a card debit account on the selected Journal"))
        if not self.journal_id.card_credit_account:
            raise Warning(_("Please select a card credit account on the selected Journal"))
            
        if self.mynt_directory:
            self.extract_zip()
        else:
            raise Warning(_("Please add a zip file"))
        
        
    def extract_zip(self):
        file_data = base64.b64decode(self.mynt_directory)
        with zipfile.ZipFile(BytesIO(file_data)) as data:
            filenames_csv = [filename for filename in data.namelist() if filename.endswith('.csv')]  # A list of filenames that end with .csv, this is used since i don't know what the csv file is called or if there are several of them.
            
            for filename in filenames_csv:
                data_read = data.read(filename) # Is a byte string now with "\r\n" in it.
                data_read = data_read.decode("utf-8").split("\r\n") #Seem to have to make into regular string and make a list split on "\r\n" for the csv parser to work
                csv_reader = csv.DictReader(data_read)
                line_count = 0
                # Column names are Date, Account, Amount, Currency, Original amount, Original currency, VAT amount, VAT rate, Description, Category, Comment, Filename, Settlement status, Person, Card number, Accounting status, Cost center, Project
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
                        account_move = self.create_account_move(row,"debit")
                        self.create_account_card_statement_line(row,account_move,account_card_statement_id)
                        total_amount += account_move.amount_total
                    elif float(row["Amount"]) >= 0:#Is a credit transaction
                        account_move = self.create_account_move(row,"credit")
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
                card_credit_account = self.journal_id.card_credit_account
                card_debit_account = self.journal_id.card_debit_account
                
                payment_account_move = self.env['account.move'].with_context(check_move_validity=False).create({'journal_id': self.journal_id.id,"move_type":'in_invoice',"ref": "Mynt Samling",'date':reverse_move_date,'invoice_date':reverse_move_date,'period_id':reverse_move_period_id})
                account_move_line = self.env['account.move.line'].with_context(check_move_validity=False)
                debit_line = account_move_line.create({
                    'account_id': card_debit_account.id,
                    'debit': total_amount,
                    'exclude_from_invoice_tab': False,
                    'move_id': payment_account_move.id,
                })
                credit_line = account_move_line.create({
                    'account_id': card_credit_account.id,
                    'credit': total_amount,
                    'exclude_from_invoice_tab': True,
                    'move_id': payment_account_move.id,
                })  
                payment_account_move.with_context(check_move_validity=False)._recompute_dynamic_lines()
                account_card_statement_id.account_move_id = payment_account_move.id
                account_card_statement_id.journal_id = self.journal_id
                self.env['ir.attachment'].create({
                                'name': filename,
                                'type': 'binary',
                                'res_model':"account.card.statement",
                                'res_id': account_card_statement_id.id,
                                'datas':self.mynt_directory,
                            })
            
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
    
    def create_account_move(self, row, credit_or_debit):
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
        if vat_rate == 0:
            tax_account = self.env["account.tax"].search([("name","=","MF"),("amount","=","0")])
        elif vat_rate == 6:
            tax_account = self.env["account.tax"].search([("name","=","I6"),("amount","=","6")])
        elif vat_rate == 12:
            tax_account = self.env["account.tax"].search([("name","=","I12"),("amount","=","12")])
        elif vat_rate == 25:
            tax_account = self.env["account.tax"].search([("name","=","I"),("amount","=","25")])
        else: # Default to 25% seems like the safest way of handling weird input data, maybe the should throw an error, since 0%,6%,12% and 25% vat are the only valid ones here in sweden.
            to_check = True
            tax_account = self.env["account.tax"].search([("name","=","I")])
        if not tax_account:
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
        move_type = "in_receipt"
        if float(row.get('Amount')) > 0:
            move_type = "entry"
            
        period_id = self.env['account.period'].date2period(datetime.strptime(row.get("Date"), '%Y-%m-%d'))
        account_move = self.env['account.move'].with_context(check_move_validity=False).create({
            'partner_id':partner_id,
            'journal_id': self.journal_id.id,
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
        move_line = account_move_line.create({
            'account_id': account.id,
            'credit': credit_amount,
            'debit': debit_amount,
            'exclude_from_invoice_tab': False,
            'move_id': account_move.id,
            'name': row.get("Category","")+" "+row.get("Comment",""),
            'tax_ids':[(6, 0, [tax_account.id])],
        })
        move_line._onchange_mark_recompute_taxes()
        account_move.with_context(check_move_validity=False)._recompute_dynamic_lines()
        return account_move
        
   
