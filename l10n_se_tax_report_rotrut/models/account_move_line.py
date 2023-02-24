from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_rotrut = fields.Boolean(string='Rot/Rut-avdrag', related='journal_id.is_rotrut')
    rotrut_id = fields.Many2one('account.rotrut', string='Utfört arbete', store=True)
    rotrut_percent = fields.Float(string='Rot/Rut procent')
    is_material = fields.Boolean(string='Material', default=False, store=True)
    invoice_rotrut_line_id = fields.Many2one('account.move.line', string='field_name')
    uuid = fields.Char()
    is_obsolete = fields.Boolean()

    @api.onchange('rotrut_id')
    def _set_default_percent(self):
        for line in self:
            if line.rotrut_id.rotrut == 'rot':
                if line.is_material == False:
                    line.rotrut_percent = 30
            elif line.rotrut_id.rotrut == 'rut':
                if line.is_material == False:
                    line.rotrut_percent = 50
    
    @api.onchange('is_material')
    def _material_cost_percent(self):
        if self.is_material == True:
            self.rotrut_percent = 0
        elif self.rotrut_id.rotrut == 'rot':
            self.rotrut_percent = 30
        elif self.rotrut_id.rotrut == 'rut':
            self.rotrut_percent = 50
    
    @api.onchange('is_material')
    def _set_account_id(self):
        if self.is_material == True:
            _logger.warning(f"{self.account_id=}")
            rotrut_account = self.env['account.account'].search([('code','=','3222')])
            self.account_id = rotrut_account.id
        elif self.is_material == False:
            account = self.product_id.product_tmpl_id.get_product_accounts()
            if account:
                self.account_id = account['income']
            else:
                account = self.default_get('account_id')
                self.account_id = self.env['account.account'].browse(account['account_id'])


    


    # @api.model
    # def create(self, vals):
    #     res = super(AccountMoveLine, self).create(vals)
    #     _logger.warning('000000000000000000000000000000000000000000000000000000000000000')
    #     _logger.warning(res)
    #     if not self.exclude_from_invoice_tab:
    #         self._extra_journal_line(res)
    #     return res

    # def _extra_journal_line(self, res):
    #     _logger.warning('move_id = %s' % res.move_id)
    #     # res.move_id.line_ids = [(0, 0, {
    #     #      "account_id": self.env['account.account'].search([('code','=','3001')]).id,
    #     #      "debit": res.credit * 1.25 * 0.50,
    #     #      "exclude_from_invoice_tab": True,
    #     #      "recompute_tax_line": True,

    #     # })]
    #     res.move_id.write({
    #         'line_ids': (0, 0, {
    #             "account_id": self.env['account.account'].search([('code','=','3001')]).id,
    #             # "name": iline.name,
    #             # "product_uom_id": iline.product_uom_id,
    #             # "rotrut_id": iline.rotrut_id,
    #             "invoice_rotrut_line_id": res.id,
    #             "debit": res.credit * 1.25 * 0.50,
    #             "exclude_from_invoice_tab": True,
    #             "recompute_tax_line": True,
    #         })

    #     })
           