import logging
from datetime import datetime

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class SkatteverketAuth(http.Controller):

    @http.route('/skattekonto',type='http', auth='public', website=True) 
    def authenticate_tax_account(self, **kw):
        state = kw.get("state")
        auth_code = kw.get("code")
        token_response = {}

        journal_env = request.env["account.journal"].sudo()
        partner_id = request.env["res.partner"].sudo()

        if state:
            journal_id = journal_env.search([("api_state", "=", state)],limit=1)

        if journal_id and auth_code:
            partner_id = journal_id.skatteverket_partner_id
            partner_id.authorization_code = auth_code
            token_response = self.get_access_token(journal_id,partner_id)
        
        if token_response and token_response.get("status_code") == 200:
            json_data = token_response.get("json",{})
            partner_id.access_token = json_data.get("access_token",False)
            partner_id.recived_token_on = datetime.now()
            partner_id.expires_in = json_data.get("expires_in",False)
        else:
            _logger.error(f"Failed to get access token with status code: {token_response.get("status_code","No status code provided")}")        

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

        session = journal_id.create_request_session(partner_id)
        response = session.post(url=access_token_url,headers=headers,data=payload)

        _logger.error(f"{response=}")
        _logger.error(f"{response.status_code=}")
        _logger.error(f"{response.json()=}")

        return {
            "status_code": response.status_code,
            "json": response.json()
        }