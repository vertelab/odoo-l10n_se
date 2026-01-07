import base64
import logging
import io
import tempfile
from uuid import uuid4
import requests
from requests.sessions import session as create_session
from requests_pkcs12 import Pkcs12Adapter


from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    skatteverket_partner_id = fields.Many2one(comodel_name="res.partner")
    api_state = fields.Char()
    is_valid_token = fields.Boolean(computed="")

    @api.depends("is_valid_token","skatteverket_partner_id","api_state")
    def compute_is_valid_token(self):
        for rec in self:
            if rec.skatteverket_partner_id and rec.skatteverket_partner_id.check_valid_access_token():
                rec.is_valid_token = True
            else:
                rec.is_valid_token = False

    def get_authorization(self):
        partner_id = self.skatteverket_partner_id

        if partner_id.check_valid_access_token():
            raise UserError("You already have a valid access token")

        if partner_id:

            auth_url = self.build_url("authorize")

            return {
                'type': 'ir.actions.act_url',
                'url': auth_url,
                'target': 'self',
            }

    def get_transactions(self):
        partner_id = self.skatteverket_partner_id

        if not partner_id:
            raise UserError("You need to connect this journal to a contact")
        

        if not partner_id.check_valid_access_token():
            raise UserError("You must have a valid access token to get transactions")

        headers = {
            'SKV-client_correlationid': self.create_state(),
            'Authorization': f'Bearer {partner_id.access_token}',
            'client_id': partner_id.api_client_id,
            'client_secret': partner_id.api_secret,
            'Accept': 'application/json'
            }

        url = self.build_url("beskattning")

        try:
            response = requests.get(url,headers=headers)
            if response.status_code == 200:
                res_dict = response.json()
                _logger.error(f"{res_dict=}")
            else:
                _logger.error(f"Request failed with status code: {response.status_code}")
        except Exception as e:
            _logger.error(f"Failed request with error: {e}")

    def create_state(self):
        state = str(uuid4())
        self.api_state = state
        return state

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