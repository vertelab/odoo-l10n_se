import json
from odoo import models, fields, api, _
import logging
_logger = logging.getLogger(__name__)

class AccountJournal(models.Model):
    
    _inherit = 'account.journal'

    default_credit_account_id = fields.Many2one(comodel_name='account.account', check_company=True, copy=False,
                                                ondelete='restrict', string='Default Credit Account',
                                                domain=[('deprecated', '=', False)],
                                                help="It acts as a default account for credit amount, is used for the "
                                                     "general journal type, so that we can confirm a payslip since "
                                                     "its function wants a default_credit_account_id")

    default_debit_account_id = fields.Many2one(comodel_name='account.account', check_company=True, copy=False,
                                               ondelete='restrict', string='Default Debit Account',
                                               domain=[('deprecated', '=', False)],
                                               help="It acts as a default account for debit amount, is used for the "
                                                    "general journal type, so that we can confirm a payslip since its "
                                                    "function wants a default_debit_account_id")
    
    def compute_vat_declarations(self):
        self.vat = self.env['account.vat.declaration'].search([("company_id","=",self.company_id.id)])
    
    vat = fields.Many2many("account.vat.declaration", string="Vat", compute="compute_vat_declarations")
    
    type = fields.Selection(selection_add=[('moms', 'Moms')], ondelete = {'moms':'cascade'})
    
    def _kanban_dashboard_graph(self):
        res = super()._kanban_dashboard_graph()
        _logger.error(self.company_id)
        
        _logger.warning("---------------------------------------------HEJ 1-------------------------------------------")  
        for journal in self:    
            if (journal.type == 'moms'):
                _logger.warning("---------------------------------------------HEJ 2-------------------------------------------")
                journal.kanban_dashboard_graph = json.dumps(journal._get_bar_graph_vat_datas_moms())
                
                _logger.warning("---------------------------------------------HEJ 3-------------------------------------------")     

        for journal in self:    
            _logger.warning(journal.kanban_dashboard_graph)

    def _get_bar_graph_vat_datas_moms(self):
        _logger.warning("---------------------------------------------HEJ 4-------------------------------------------")
        data = []

        # Sort self.vat by period_start.date_start in reverse order using sorted() with a key argument
        _logger.error(self.vat)
        if self.vat:
            _logger.warning("---------------------------------------------HEJ 5-------------------------------------------")
            sorted_vat = sorted(self.vat, key=lambda x: x.period_start.date_start, reverse=True)

            # Add data to list, limited to 5 most recent items
            for vat_item in sorted_vat[:5][::-1]:  # Get last 5 items and reverse the order
                data.append({
                    "label": f"{vat_item.period_start.name} - {vat_item.period_stop.name}",
                    "value": vat_item.vat_momsingavdr,
                    "type": "future"
                })
            return [{'values': data, 'title': "", 'key': "Vat: Balance", 'area': True, 'color': "future", 'is_sample_data': False}]
        
        data.append({
                    "label": f"Error",
                    "value": 500,
                    "type": "future"
                })
        return [{'values': data, 'title': "", 'key': "Vat: Balance", 'area': True, 'color': "future", 'is_sample_data': False}]
    
        