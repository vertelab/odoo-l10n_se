from odoo import _, api, fields, models
import logging
from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"
    combine_zip_file = fields.Boolean("Combine Zip File", help="Combine one several statements into one")
    
    def _create_bank_statements(self, stmts_vals, result):
        res = super()._create_bank_statements(stmts_vals, result)
        _logger.warning(f"{res=}, {stmts_vals=} {result=}")

    def _parse_file(self, data_file):
        res = super()._parse_file(data_file)
        
        journal_id = self.env['account.journal'].browse(self._context.get('journal_id'))
        # ~ _logger.warning(f"{journal_id.name=}")
        if len(res) >= 3 and len(res[2]) == 1 and journal_id.is_bankgiro_journal:
            bgnr_statment = {}
            for transaction in res[2][0]["transactions"]:
                if not transaction['bgnr_ref'] in bgnr_statment:
                    bgnr_statment[transaction['bgnr_ref']] = [transaction]
                else:
                    bgnr_statment[transaction['bgnr_ref']].append(transaction)
            y = list(res)
            y[2] = []
            for key in bgnr_statment:
                y[2].append({
                'name': key,
                'balance_start': 0.0,
                'balance_end_real': 0.0,
                'transactions': 
                bgnr_statment[key]
                ,
                'date': res[2][0]['date']
            })
            res = tuple(y)
            _logger.warning(f"{res=}")
            return res
            
        
        
        if len(res) >= 3 and len(res[2]) > 1 and self.combine_zip_file:
            all_statements = {
            'name': res[1],
            'balance_start': 0.0,
            'balance_end_real': 0.0,
            'transactions': [
            ],
            'date': '2023-04-12'
            }
            from_date = False
            to_date = False
            for transaction in res[2]:
                if not from_date:
                    from_date = transaction["date"]
                if not to_date:
                    to_date = transaction["date"]
                
                if from_date > transaction["date"]:
                   from_date = transaction["date"]
                if to_date < transaction["date"]:
                   to_date = transaction["date"]
                
                all_statements["transactions"] = all_statements["transactions"] + transaction["transactions"]
            all_statements["date"] = from_date
            all_statements['name'] = all_statements['name'] + " " +  from_date + "-" + to_date

            y = list(res)
            y[2] = [all_statements]
            res = tuple(y)

        return res
