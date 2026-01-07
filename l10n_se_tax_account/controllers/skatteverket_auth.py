import base64
import logging
import requests
import tempfile
from datetime import datetime
from requests_pkcs12 import Pkcs12Adapter

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class SkatteverketAuth(http.Controller):

    @http.route('/skattekonto',type='http', auth='user', website=True)
    def authenticate_tax_account(self, **kw):
        state = kw.get("state")
        auth_code = kw.get("code")
        token_response = False

        journal_id = request.env["account.journal"]
        partner_id = request.env["res.partner"]

        if state:
            journal_id = journal_id.search([("api_state", "=", state)],limit=1)

        if journal_id and auth_code:
            partner_id = journal_id.skatteverket_partner_id
            partner_id.authorization_code = auth_code
            token_response = self.get_access_token(journal_id,partner_id)
        
        if token_response and token_response.get("status_code") == 200:
            json_data = token_response.get("json")
            partner_id.access_token = json_data.get("access_token",False)
            partner_id.recived_token_on = datetime.now()
            partner_id.expires_in = json_data.get("expires_in",False)
        else:
            _logger.error(f"Failed to get access token with status code: {token_response.get("status_code")}")        

        redirect_url = f'/web#id={journal_id.id}&model=account.journal&view_type=form' 
        return request.redirect(redirect_url)
        
    def get_access_token(self, journal_id,partner_id):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
        }

        access_token_url = journal_id.build_url("token")
       
        payload = {
            'grant_type': 'authorization_code',
            'scope': 'ska',
            'client_id': partner_id.oauth_client_id,
            'client_secret': partner_id.oauth_secret,
            'code': partner_id.authorization_code,
            'redirect_uri': partner_id.redirect_url,
        }

        session = self.create_request_session(partner_id)
        response = session.post(url=access_token_url,headers=headers,data=payload)

        return {
            "status_code": response.status_code,
            "json": response.json()
        }

    def create_request_session(self,partner_id=None):

            session = requests.Session()

            if partner_id and partner_id.auth_method == "cert":

                cert = base64.b64decode(partner_id.certificate)
                base_url = partner_id.base_url

                with tempfile.NamedTemporaryFile(suffix=".p12", delete=False) as tmp:
                    tmp.write(cert)
                    tmp_path = tmp.name

                session.mount(
                base_url,
                Pkcs12Adapter(
                    pkcs12_filename=tmp_path,
                    pkcs12_password=partner_id.certificate_pin,
                    ),
                )

            return session