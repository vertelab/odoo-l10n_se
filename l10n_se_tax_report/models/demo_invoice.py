from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    
    @api.model
    def _demo_add_tax_lines(self, invoice_ref_id):
        record = self.env.ref(invoice_ref_id)
        record._onchange_invoice_line_ids()
        
        
class ir_config_parameter(models.Model):
    _inherit = 'ir.config_parameter'
    
    @api.model
    def _set_value_to_ir_config_parameter(self, ir_config_parameter_ref_id):
        record = self.env.ref(ir_config_parameter_ref_id)
        record.value = self.env.ref('l10n_se_tax_report.moms_journal').id

class res_partner(models.Model):
    _inherit = 'res.partner'
    
    @api.model
    def _set_property_account_position_id(self, res_partner_ref_id, region_ref):
        res_partner_record = self.env.ref(res_partner_ref_id)
        region_record = self.env.ref(region_ref)
        # ~ This if case seems pointless but im just doing what the old account_invoice.yml file did.
        if  res_partner_record.property_account_position_id !=  region_record:
            res_partner_record.property_account_position_id = region_record
