import base64
import logging
import tempfile
import requests
import time
from uuid import uuid4
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    skatteverket_partner_id = fields.Many2one(comodel_name="res.partner")
    api_state = fields.Char()

    def action_tax_account_transaction_wizard(self):
        return {
        "type": "ir.actions.act_window",
        "name": "Get Tax Account Transactions",
        "res_model": "tax_account.transaction.wizard",
        "view_mode": "form",
        "context": {"default_journal_id": self.id},
        "target": "new",
    }

    def get_authorization(self):
        partner_id = self.skatteverket_partner_id

        if partner_id.check_valid_access_token():
            raise UserError(_("You already have a valid access token"))

        if partner_id:

            auth_url = self.build_url("authorize")

            if partner_id.auth_method == "cert":
                if not partner_id.certificate:
                    raise UserError(_("No certificate uploaded on the partner"))
                self.auth_cert_get_request(auth_url,partner_id)
            elif partner_id.auth_method == "e_id":
                return {
                    'type': 'ir.actions.act_url',
                    'url': auth_url,
                    'target': 'self',
                }


    @api.model
    def _cron_tax_account(self):
        journal_ids = self.env["account.journal"].search([("skatteverket_partner_id", "!=", False)])
        filtered_journal_ids = journal_ids.filtered(lambda j: j.skatteverket_partner_id.auth_method == "cert" and j.skatteverket_partner_id.certificate)
        for journal_id in filtered_journal_ids:
            partner_id = journal_id.skatteverket_partner_id
            if not partner_id.check_valid_access_token():
                auth_url = journal_id.build_url("authorize")
                journal_id.auth_cert_get_request(auth_url,partner_id)
                time.sleep(5) # Wait untill we recive a access token
            transaction_wizard_id = self.env["tax_account.transaction.wizard"].create({
                "journal_id": journal_id.id,
                "date_from": fields.Date.today() - relativedelta(days=1)
            })
            transaction_wizard_id.get_transactions()

    def create_state(self):
        state = str(uuid4())
        self.api_state = state
        self.env.cr.commit()
        return state

    def auth_cert_get_request(self,url,partner_id):
        session = self.create_request_session(partner_id)
        response = session.get(url)

        return response

    def create_request_session(self,partner_id=None):

        session = requests.Session()

        if partner_id and partner_id.auth_method == "cert":
            cert = base64.b64decode(partner_id.certificate)

            with tempfile.NamedTemporaryFile(suffix=".pem", delete=False) as tmp:
                tmp.write(cert)
                tmp_path = tmp.name

            session.cert = tmp_path

        return session

    def build_url(self,type):
        partner_id = self.skatteverket_partner_id
        redirect_url = partner_id.redirect_url
        client_id = partner_id.oauth_client_id
        state = self.create_state()
        base_url = partner_id.base_url
        scope = "ska"

        base_url = base_url if base_url[-1] == "/" else base_url + "/"
        base_url = base_url if "https://" in base_url else "https://" + base_url

        base_url = base_url.replace("https://","https://test.") if partner_id.test_mode and "test" not in base_url.split(".") else base_url 

        if type == "authorize" or type == "token":
            base_url = base_url.replace("https://","https://peroauth2.") + "oauth2/v1/per/"            

        if partner_id.auth_method == "cert":
            base_url = base_url.replace("per","org")

        base_url = f"{base_url}{type}"

        if type == "authorize":
            base_url = base_url + (
                f'?client_id={client_id}'
                f'&response_type=code'
                f'&state={state}'
                f'&redirect_uri={redirect_url}'
                f"&scope={scope}"
                )
        elif type == "beskattning":
            base_url = base_url.replace("https://","https://api.")
            base_url = base_url + f"/skattekonto/v2/skattekonton/{self.bank_account_id.acc_number}/transaktioner"

        _logger.error(f"{base_url=}")

        return base_url