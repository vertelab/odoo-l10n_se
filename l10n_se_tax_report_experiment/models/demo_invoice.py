from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.model
    def _demo_add_tax_lines(self,invoice_ref_id):
        record = self.env.ref(invoice_ref_id)
        record._onchange_invoice_line_ids()
        
        

