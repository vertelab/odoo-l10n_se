from odoo import api, fields, models, _
import logging
_logger = logging.getLogger(__name__)

class account_invoice(models.Model):
    _inherit = 'account.invoice'

    @api.multi
    def create_demo_invoices(self,customer_id,product_ids,):
        _logger.warning("jakmar: costumer_id %s product_ids %s" %(customer_id,product_ids))


 #~ !record {model: account.invoice, id: demo_invoice_1}:
    #~ partner_id: l10n_se.res_partner_2
    #~ reference_type: none
    #~ payment_term_id: account.account_payment_term
    #~ type: 'out_invoice'
    #~ date_invoice: !eval time.strftime('%Y')+'-03-14'
    #~ invoice_line_ids:
      #~ - product_id: l10n_se.product_product_1
        #~ price_unit: 2500.0
        #~ quantity: 2
#~ -
  #~ !python {model: account.invoice, id: demo_invoice_1}: |
    #~ if self.state == 'draft':
        #~ import time
        #~ self._onchange_partner_id()
        #~ self._onchange_journal_id()
        #~ self.invoice_line_ids._onchange_product_id()
        #~ self.invoice_line_ids._onchange_account_id()
        #~ self._onchange_invoice_line_ids()
        #~ self.action_invoice_open()
        #~ if self.partner_id.customer:
            #~ method = self.env.ref('account.account_payment_method_manual_in')
        #~ else:
            #~ method = self.env.ref('account.account_payment_method_manual_out')
        #~ payment = self.env['account.payment'].create({
          #~ 'invoice_ids': [(4, self.id, None)],
          #~ 'payment_date': time.strftime('%Y')+'-04-14',
          #~ 'partner_type': 'customer' if self.partner_id.customer else 'supplier',
          #~ 'partner_id': self.partner_id.id,
          #~ 'journal_id': self.env['account.journal'].search([('code', '=', 'BNK1')]).id,
          #~ 'payment_type': 'inbound' if self.partner_id.customer else 'outbound',
          #~ 'payment_method_id': method.id,
          #~ 'payment_method_code': method.code,
          #~ 'amount': self.amount_total,
        #~ })
        #~ payment.post()
#~ -
