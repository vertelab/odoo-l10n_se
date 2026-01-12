import logging
import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class TaxAccountTransactionWizard(models.TransientModel):
    _name = 'tax_account.transaction.wizard'
    _description = 'A wizard to specify the from date when getting tax account transactions.'

    journal_id = fields.Many2one(comodel_name="account.journal",required=True)
    date_from = fields.Date(help="This field will tell the tax account api the from date to get transactions. If this field is not set it will defult to 555 days ago. It will not get transaction that are older then 915 days.")

    def get_transactions(self):
        partner_id = self.journal_id.skatteverket_partner_id

        if not partner_id:
            raise UserError("You need to connect this journal to a contact")
        

        if not partner_id.check_valid_access_token():
            raise UserError("You must have a valid access token to get transactions")

        headers = {
            'SKV-client_correlationid': self.journal_id.create_state(),
            'Authorization': f'Bearer {partner_id.access_token}',
            'client_id': partner_id.api_client_id,
            'client_secret': partner_id.api_secret,
            'Accept': 'application/json'
            }

        url = self.journal_id.build_url("beskattning")

        if self.date_from:
            url = f"{url}?datumFrom={self.date_from}"

        resp_dict = {}

        try:
            response = requests.get(url,headers=headers)
            if response.status_code == 200:
                resp_dict = response.json()
                _logger.error(f"{resp_dict=}")
            else:
                _logger.error(f"Request failed with status code: {response.status_code}")
        except Exception as e:
            _logger.error(f"Failed request with error: {e}")
        
        bank_statement_id = self.create_bank_statement(resp_dict)
        self.create_bank_statement_lines(resp_dict,bank_statement_id)

    def create_bank_statement(self,resp_dict):
        bank_statement = self.env["account.bank.statement"]
        ocr_number = resp_dict.get("ocrNummer")
        bank_statement_id = bank_statement.search([("name", "=", ocr_number),("journal_id", "=", self.journal_id.id)],limit=1)
        if not bank_statement_id:
            bank_statement_id = self.env["account.bank.statement"].create({
                "name": ocr_number,
            })
        return bank_statement_id

    def create_bank_statement_lines(self,resp_dict,bank_statement_id):
        transactions = resp_dict.get("tidigareTransaktioner")
        bank_statement_line = self.env["account.bank.statement.line"]
        bank_statement_line_ids = []
        for transaction in transactions:
            transaction_uuid = transaction.get("transaktionsidentitet")
            bank_statement_line_id = bank_statement_line.search([
                ("statement_id", "=", bank_statement_id.id),
                ("journal_id", "=", self.journal_id.id),
                ("name", "=", transaction_uuid)
                ],limit=1)
            if not bank_statement_line_id:
                bank_statement_line_id = bank_statement_line.create({
                    "name": transaction_uuid,
                    "journal_id": self.journal_id.id,
                    "statement_id": bank_statement_id.id,
                    "date": transaction.get("transaktionsdatum"),
                    "ref": transaction.get("transaktionstext"),
                    "amount": transaction.get("beloppKronofogden") if transaction.get("beloppSkatteverket") == None else transaction.get("beloppSkatteverket")
                })
            bank_statement_line_ids.append(bank_statement_line_id)
        return bank_statement_line_ids