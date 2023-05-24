from odoo import _, api, fields, models
import logging
from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"
    combine_zip_file = fields.Boolean("Combine Zip File", help="Combine one several statements into one")

    def _parse_file(self, data_file):
        res = super()._parse_file(data_file)
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
