import base64
import logging
import io
from uuid import uuid4
from requests.sessions import session as create_session
from requests_pkcs12 import Pkcs12Adapter


from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    _inherit = 'account.journal'

    skatteverket_partner_id = fields.Many2one(comodel_name="res.partner")

    def get_authorization_code(self):

        

        if self.skatteverket_partner_id:
            session = create_session()

            cert = io.BytesIO(base64.b64decode(self.skatteverket_partner_id.certificate))
            base_url = skatteverket_partner_id.base_url

            session.mount(
            base_url,
            Pkcs12Adapter(
                pkcs12_filename=cert,
                pkcs12_password=self.cretificate_pin,
                ),
            )

            auth_url = self.build_authorization_code_url(self.skatteverket_partner_id)

            session.get(auth_url,allow_redirects=True)

    def build_authorization_code_url(self,partner_id):
        base_url = partner_id.base_url
        redirect_url = partner_id.redirect_url
        client_id = partner_id.oauth_client_id
        state = uuid4()
        auth_url = (
            f"{base_url}/oauth2/v1/org/authorize"
            f"?client_id={client_id}"
            "&response_type=code"
            f"&state={state}"
            f"&redirect_uri={redirect_url}"
        )
        return auth_url

    
    @api.model
    def check_params(partner_id):
        if partner_id and \
        partner_id.certificate:
            return True
        return False