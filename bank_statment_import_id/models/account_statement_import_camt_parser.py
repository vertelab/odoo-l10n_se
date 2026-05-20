from odoo import models


class AccountStatementImportCamtParser(models.AbstractModel):
    _inherit = "account.statement.import.camt.parser"

    def parse_entry(self, ns, node):
        ntry_ref_node = node.xpath("./ns:NtryRef", namespaces={"ns": ns})
        ntry_ref = ntry_ref_node[0].text if ntry_ref_node else None
        for transaction in super().parse_entry(ns, node):
            if not transaction.get("unique_import_id"):
                transaction["unique_import_id"] = (
                    ntry_ref
                    if ntry_ref
                    else f"{transaction.get('date', 'nodate')}-"
                         f"{transaction.get('amount', 0)}"
                )
            yield transaction
