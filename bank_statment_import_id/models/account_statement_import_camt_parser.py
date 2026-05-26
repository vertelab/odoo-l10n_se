from odoo import models


class AccountStatementImportCamtParser(models.AbstractModel):
    _inherit = "account.statement.import.camt.parser"

    def parse_transaction_details(self, ns, node, transaction):
        """
        Overridden to try and find a unique ID at the transaction detail level.
        """
        super().parse_transaction_details(ns, node, transaction)
        
        # Try to find a unique ID at the detail level (Transaction ID or End to End ID)
        tx_id_node = node.xpath("./ns:Refs/ns:TxId", namespaces={"ns": ns})
        if tx_id_node and tx_id_node[0].text:
            transaction["unique_import_id"] = tx_id_node[0].text
        else:
            e2e_id_node = node.xpath("./ns:Refs/ns:EndToEndId", namespaces={"ns": ns})
            if e2e_id_node and e2e_id_node[0].text:
                transaction["unique_import_id"] = e2e_id_node[0].text

    def parse_entry(self, ns, node):
        """
        Overridden to ensure unique_import_id is unique even if multiple transactions
        belong to the same entry.
        """
        # Entry level reference (NtryRef)
        ntry_ref_node = node.xpath("./ns:NtryRef", namespaces={"ns": ns})
        ntry_ref = ntry_ref_node[0].text if ntry_ref_node else None
        
        # Fallback to AcctSvcrRef at Entry level if NtryRef is missing
        if not ntry_ref:
            asrv_ref_node = node.xpath("./ns:AcctSvcrRef", namespaces={"ns": ns})
            ntry_ref = asrv_ref_node[0].text if asrv_ref_node else None

        # Iterate through transactions yielded by the base parser
        for i, transaction in enumerate(super().parse_entry(ns, node)):
            if not transaction.get("unique_import_id"):
                # Use Entry Ref + index to guarantee uniqueness within the file
                # while remaining stable across multiple imports of the same file.
                if ntry_ref:
                    transaction["unique_import_id"] = f"{ntry_ref}-{i}"
                else:
                    # Final fallback using date and amount
                    transaction["unique_import_id"] = (
                        f"{transaction.get('date', 'nodate')}-"
                        f"{transaction.get('amount', 0)}-{i}"
                    )
            yield transaction
