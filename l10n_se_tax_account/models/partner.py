import logging
from requests.sessions import session

from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError, ValidationError

_logger = logging.getLogger(__name__)

class ResPartner(models.Model):
    _inherit = 'res.partner'


    enable_skatteverket_api = fields.Boolean()
    certificate = fields.Binary()
    certificate_pin = fields.Char()
    base_url = fields.Char()
    return_url = fields.Char()
    oauth_client_id = fields.Char()
    oauth_secret = fields.Char()
    authorization_code = fields.Char()