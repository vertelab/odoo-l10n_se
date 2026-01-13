import logging
from requests.sessions import session
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'

    enable_skatteverket_api = fields.Boolean()
    auth_method = fields.Selection(selection=[("e_id","E-ID"),("cert","Certificate")], default="e_id")
    test_mode = fields.Boolean(default=True)
    certificate = fields.Binary()
    certificate_pin = fields.Char()
    base_url = fields.Char(help="Base URL Exsample: https://skatteverket.se/, skatteverket.se")
    redirect_url = fields.Char()
    oauth_client_id = fields.Char()
    oauth_secret = fields.Char()    
    api_client_id = fields.Char()
    api_secret = fields.Char()
    authorization_code = fields.Char()
    recived_token_on = fields.Datetime()
    expires_in = fields.Integer()
    access_token = fields.Char()

    def check_valid_access_token(self):
        if self.access_token and self.recived_token_on and self.recived_token_on + relativedelta(seconds=self.expires_in) > fields.datetime.now():
            return True
        else:
            return False