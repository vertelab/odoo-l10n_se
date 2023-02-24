from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import uuid

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    is_rotrut = fields.Boolean(string='Rot/Rut-avdrag', related='journal_id.is_rotrut')
    rotrut_lines = fields.Monetary(string="Rot/Rut jobbkostnad")
    rotrut_amount = fields.Monetary(string="Rot/Rut avdrag", compute='_compute_amount')

    material_error = 'Materialkostnad kan endast vara ikryssad på produkter med utfört arbete!'

    #@api.onchange('line_ids','invoice_line_ids')
    def _onchange_recompute_dynamic_rotrutlines(self):
        #_logger.warning(uuid.uuid4())
        for move in self:
            rotrut_workcost_account = move.journal_id.rotrut_workcost_account_id
            rotrut_material_account = move.journal_id.rotrut_material_account_id
            rotrut_receivable_account = move.journal_id.rotrut_receivable_account_id
            #_logger.warning(f"{move=}")
            line_vals = []
            for line in move.line_ids:
                line_default_account_id = line.account_id
                #_logger.warning()
                if line.rotrut_id:
                    #if line.account_id.code != '3221':
                    if line.account_id != rotrut_workcost_account:
                        if line.is_material:
                            #rotrut_account = self.env['account.account'].search([('code','=','3222')])
                            rotrut_account = rotrut_material_account
                        else:
                            #rotrut_account = self.env['account.account'].search([('code','=','3221')])
                            rotrut_account = rotrut_workcost_account
                        line.account_id = rotrut_account.id
                        line.uuid = str(uuid.uuid4())

                        #account_type = self.env['account.account'].search([('code','=','1513')]).user_type_id
                        account_type = rotrut_receivable_account.user_type_id
                        _logger.warning(account_type)
                        self.env['account.account'].search([('code','=','1513')]).user_type_id = 13
                        #self.env['account.account'].search([('code','=','1513')]).user_type_id = self.env.ref('')
                        _logger.warning(self.env['account.account'].search([('code','=','1513')]).user_type_id)

                        line_vals.append(
                            (0,0,{
                            #"account_id": self.env['account.account'].search([('code','=','1513')]),
                            "account_id": rotrut_receivable_account,
                            #"name": iline.name,
                            #"product_uom_id": iline.product_uom_id,
                            #"rotrut_id": iline.rotrut_id,
                            #"invoice_rotrut_line_id": iline.id,
                            "uuid": line.uuid,
                            "debit": line.credit * 1.25 * line.rotrut_percent / 100,
                            "exclude_from_invoice_tab": True,
                            "recompute_tax_line": True,
                        }))
                        if line_vals:
                            #_logger.warning(line_vals)
                            move.update({'line_ids':line_vals})
                            #self.env['account.account'].search([('code','=','1513')]).user_type_id = account_type

                    #elif line.account_id.code == '3221':
                    elif line.account_id == rotrut_workcost_account:
                        for line3001 in move.line_ids:
                            if line3001.uuid == line.uuid:
                                line3001.debit = line.credit * 1.25 * line.rotrut_percent / 100
                                #account_type = self.env['account.account'].search([('code','=','1513')]).user_type_id
                                #_logger.warning(account_type)
                                break



    def _recompute_dynamic_lines(self, recompute_all_taxes=False, recompute_tax_base_amount=False):
        line_obj = self.fetch_leftover_rotrut_line()
        if line_obj:
            line_obj.is_obsolete = True
            self.line_ids = self.line_ids.filtered(lambda line: not line.is_obsolete)
            self.line_ids.recompute_tax_line = True
        self._onchange_recompute_dynamic_rotrutlines()
        #self.env['account.account'].search([('code','=','1513')]).user_type_id = 1
        res = super()._recompute_dynamic_lines(recompute_all_taxes,recompute_tax_base_amount)
        return res



    def fetch_leftover_rotrut_line(self):
        line_uuid = None
        for move in self:
            rotrut_workcost_account = move.journal_id.rotrut_workcost_account_id
            rotrut_receivable_account = move.journal_id.rotrut_receivable_account_id
            for line3001 in move.line_ids:
                #if line3001.account_id.code == '1513':
                if line3001.account_id == rotrut_receivable_account:
                    line_uuid = line3001.uuid
                    exists = False
                    for line3221 in move.line_ids:
                        #if line3221.account_id.code == '3221':
                        if line3221.account_id == rotrut_workcost_account:
                            _logger.warning(line3221.uuid)
                            if line3221.uuid == line_uuid:
                                _logger.warning('tjoho')
                                exists = True
                    if not exists:
                        #move.update({'line_ids': [3,line3001._origin.id,0]})
                        _logger.warning(line3001._origin.id)
                        return line3001
        return False


    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'line_ids.rotrut_percent',
        'is_rotrut',
    )
    def _compute_amount(self):
        super()._compute_amount()
        self.rotrut_lines = 0
        self.rotrut_amount = 0
        line = None
        for move in self:

            for line in move.line_ids:
                if line.rotrut_id:
                    line_with_tax = line.price_subtotal * (1 + line.tax_ids.amount / 100)
                    move.rotrut_lines += line_with_tax
                    move.rotrut_amount += (line_with_tax * line.rotrut_percent / 100)

            if move.is_rotrut:
                move.rotrut_amount = -abs(move.rotrut_amount)   # make rotrut_amount a negative value
                move.amount_total += move.rotrut_amount
                move.amount_total_signed += move.rotrut_amount
                move.amount_residual = move.amount_total
                move.amount_residual_signed = move.amount_total
    
    def write(self,vals):
        if 'line_ids' in vals:
            for line in vals['line_ids']:
                if line[0] == 1 and type(line[2]) is dict:
                    elem = line[2]
                    id = line[1]
                    if type(elem) is dict:
                        material = elem.get('is_material','notset')
                        if material == 'notset':
                            material = self.env['account.move.line'].browse(id).is_material
                        rotrut_id = elem.get('rotrut_id','notset')
                        if rotrut_id == 'notset':
                            rotrut_id = self.env['account.move.line'].browse(id).rotrut_id
                        if rotrut_id == False and material == True:
                            raise UserError(self.material_error)
        super().write(vals)

    @api.model
    def create(self,vals):
        if 'invoice_line_ids' in vals:
            for line in vals['invoice_line_ids']:
                elem = line[2]
                if type(elem) is dict:
                    if 'is_material' in elem and 'rotrut_id' in elem:
                        if elem.get('is_material') == True and elem.get('rotrut_id') == False:
                            raise UserError(self.material_error)
        record = super().create(vals)
        return record

