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
        if not self.journal_id:
            raise Warning(_("Please select a journal"))
            
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
                for row in csv_reader:
                    if line_count == 0:
                        _logger.warning(f'Column names are {", ".join(row)}')
                    line_count += 1
                    
                    if float(row["Amount"]) < 0: #Is a debit transaction
                        account_move = self.create_credit_account_move(row)
                    # ~ else:#Is a credit transaction
                        # ~ account_move = self.create_debit_account_move(row)
                        
                     # ~ #Add Attachment
                    if row["Filename"] and row["Filename"] in data.namelist() : 
                        self.env['ir.attachment'].create({
                            'name': row["Filename"],
                            'type': 'binary',
                            'res_model': "account.move",
                            'res_id': account_move.id,
                            'datas': base64.b64encode(data.read(row["Filename"])),
                        })    

                _logger.warning(f'Processed {line_count} lines.')
                
    def create_credit_account_move(self, row):
        amount = float(row["Amount"])  * (-1.0)
        if row["VAT amount"] == "":
           row["VAT amount"] = "0.0" 
        tax_amount = float(row["VAT amount"]) * (-1.0)
        amount_without_tax = amount - tax_amount
        
        if row["VAT rate"] == "":
           row["VAT rate"]  = "0.0" 
        vat_rate = float(row["VAT rate"].replace("%",""))
        if vat_rate == 0:
            tax_account = self.env["account.tax"].search([("name","=","MF"),("amount","=","0")])
        elif vat_rate == 6:
            tax_account = self.env["account.tax"].search([("name","=","I6"),("amount","=","6")])
        elif vat_rate == 12:
            tax_account = self.env["account.tax"].search([("name","=","I12"),("amount","=","12")])
        elif vat_rate == 25:
            tax_account = self.env["account.tax"].search([("name","=","I"),("amount","=","25")])
        else: # Default to 25% seems like the safest way of handling weird input data, maybe the should throw an error, since 0%,6%,12% and 25% vat are the only valid ones here in sweden.
            # ~ continue
            # raise ValidationError(f"No valid tax account found, for vat rate {vat_rate}")
            tax_account = self.env["account.tax"].search([("name","=","I")])
        if not tax_account:
            raise ValidationError(f"No valid tax account found, for vat rate {vat_rate}")
            
        credit_account = self.journal_id.default_account_id #changed
        if not credit_account:
            raise ValidationError(f"No valid credit account found, please set it on your selected journal")
            
        debit_account = self.env["account.account"].search([("code","=",row["Account"])])
        if not debit_account:
            debit_account = self.env["account.account"].search([("code","=","4001")])
            
        account_move = self.env['account.move'].with_context(check_move_validity=False).create({'journal_id': self.journal_id.id,"move_type":'in_invoice'})
        account_move_line = self.env['account.move.line'].with_context(check_move_validity=False)
        debit_line = account_move_line.create({
            'account_id': debit_account.id,
            # ~ 'name': row["Description"],
            'debit': amount_without_tax,
            'exclude_from_invoice_tab': True,
            'move_id': account_move.id,
            'name': row["Person"] + ":" + row["Description"],
            'tax_ids':[(6, 0, [tax_account.id])],
        })
        debit_line._onchange_mark_recompute_taxes()
        account_move.with_context(check_move_validity=False)._recompute_dynamic_lines()
        
        # ~ credit_line = account_move_line.create({
            # ~ 'account_id': credit_account.id, #CHANGED
            # ~ 'name': row["Description"],
            # ~ 'credit': amount,
            # ~ 'exclude_from_invoice_tab': True,
            # ~ 'move_id': account_move.id,
        # ~ })      
        
        return account_move
        
    def create_debit_account_move(self, row):
        amount = float(row["Amount"])
        credit_account = self.env["account.account"].search([("code","=",row["Account"])])
        if not credit_account:
            credit_account = self.env["account.account"].search([("code","=","3001")])
            
        debit_account = self.env["account.account"].search([("code","=","1930")])
        if not debit_account:
            raise ValidationError(f"No valid debit_account found, 1930 seems to be missing")
            
        account_move = self.env['account.move'].with_context(check_move_validity=False).create({'journal_id': self.journal_id.id})
        account_move_line = self.env['account.move.line'].with_context(check_move_validity=False)
        credit_line = account_move_line.create({
            'account_id': credit_account.id,
            'name': row["Description"],
            'credit': amount,
            'exclude_from_invoice_tab': True,
            'move_id': account_move.id,
            'name': row["Person"] + ":" + row["Description"],
        })
        credit_line._onchange_mark_recompute_taxes()
        account_move.with_context(check_move_validity=False)._recompute_dynamic_lines()
        
        debit_line = account_move_line.create({
            'account_id': debit_account.id, 
            # ~ 'name': row["Description"],
            'debit': amount,
            'exclude_from_invoice_tab': True,
            'move_id': account_move.id,
        })
                    
        
