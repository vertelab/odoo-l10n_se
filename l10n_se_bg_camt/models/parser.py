"""Class to parse camt files."""
# Copyright 2013-2016 Therp BV <https://therp.nl>
# Copyright 2017 Open Net Sàrl
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import re

from lxml import etree

from odoo import _, api, fields, models
import logging
from odoo.exceptions import except_orm, Warning, RedirectWarning, UserError, ValidationError

_logger = logging.getLogger(__name__)

class CamtParser(models.AbstractModel):
    _inherit = "account.statement.import.camt.parser"
    
    def get_bank_giro_account(self, ns, node):
        # ~ _logger.warning("get_bank_giro_account"*100)    
        is_bgnr_account = False
        ##Don't know if this will always be the case but it seems that if there is dbtr_bgnr_nodes then those are the ones that is our own bankgiro account. Else we controll the cdtr_bgnr_nodes.
        cdtr_bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:CdtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        dbtr_bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:DbtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        
        if dbtr_bgnr_nodes:
            bgnr_nodes = dbtr_bgnr_nodes
        else:
            bgnr_nodes = cdtr_bgnr_nodes
            
        for bgnr_node in bgnr_nodes:
            is_bgnr = bgnr_node.xpath("./ns:SchmeNm/ns:Prtry", namespaces={"ns": ns})
            if is_bgnr[0].text != "BGNR":
                continue
                
            if is_bgnr_account and is_bgnr_account != bgnr_node.xpath("./ns:Id", namespaces={"ns": ns})[0].text:
                raise UserError(f'There are deposits for different bankgiro accounts. {is_bgnr_account} {bgnr_node.xpath("./ns:Id", namespaces={"ns": ns})[0].text}')
            is_bgnr_account = bgnr_node.xpath("./ns:Id", namespaces={"ns": ns})[0].text
        return is_bgnr_account
        

    
    
    def parse(self, data):
        if self._context.get('journal_id',False) and self.env['account.journal'].browse(self._context.get('journal_id',False)) and not self.env['account.journal'].browse(self._context.get('journal_id',False)).is_bankgiro_journal:
            return super(CamtParser, self).parse(data)
            
        """Parse a camt.052 or camt.053 or camt.054 file."""
        try:
            root = etree.fromstring(data, parser=etree.XMLParser(recover=True))
        except etree.XMLSyntaxError:
            try:
                # ABNAmro is known to mix up encodings
                root = etree.fromstring(data.decode("iso-8859-15").encode("utf-8"))
            except etree.XMLSyntaxError:
                root = None
        if root is None:
            raise ValueError("Not a valid xml file, or not an xml file at all.")
        ns = root.tag[1 : root.tag.index("}")]
        self.check_version(ns, root)
        statements = []
        currency = None
        account_number = None
        for node in root[0][1:]:
            statement = self.parse_statement_bgnr(ns, node)
            if len(statement["transactions"]):
                if "currency" in statement:
                    currency = statement.pop("currency")
                if "account_number" in statement:
                    account_number = statement.pop("account_number")
                statements.append(statement)
        return currency, account_number, statements
    
    
    def parse_statement_bgnr(self, ns, node):
        """Parse a single Stmt node."""
        result = {}
        self.add_value_from_node(
            ns,
            node,
            ["./ns:Acct/ns:Id/ns:IBAN", "./ns:Acct/ns:Id/ns:Othr/ns:Id"],
            result,
            "account_number",
        )
        
        self.add_value_from_node(ns, node, "./ns:Id", result, "name")
        self.add_value_from_node(
            ns,
            node,
            [
                "./ns:Acct/ns:Ccy",
                "./ns:Bal/ns:Amt/@Ccy",
                "./ns:Ntry/ns:Amt/@Ccy",
            ],
            result,
            "currency",
        )
        result["balance_start"], result["balance_end_real"] = self.get_balance_amounts(
            ns, node
        )
        entry_nodes = node.xpath("./ns:Ntry", namespaces={"ns": ns})
        for entry_node in entry_nodes:
            bank_giro_account = self.get_bank_giro_account(ns, entry_node)
            result['account_number'] = bank_giro_account
        transactions = []
        
        
    
        for entry_node in entry_nodes:
            transactions.extend(self.parse_entry_bgnr(ns, entry_node))
        result["transactions"] = transactions
        result["date"] = None
        if transactions:
            result["date"] = sorted(
                transactions, key=lambda x: x["date"], reverse=True
            )[0]["date"]
        return result

    def parse_amount_bgnr(self, ns, node):
        """Parse element that contains Amount and CreditDebitIndicator."""
        if node is None:
            return 0.0
        sign = 1
        amount = 0.0
        sign_node = node.xpath("ns:CdtDbtInd", namespaces={"ns": ns})
        if not sign_node:
            sign_node = node.xpath("../../ns:CdtDbtInd", namespaces={"ns": ns})
        if sign_node and sign_node[0].text == "CRDT":
            sign = -1
        amount_node = node.xpath("ns:Amt", namespaces={"ns": ns})
        if not amount_node:
            amount_node = node.xpath(
                "./ns:AmtDtls/ns:TxAmt/ns:Amt", namespaces={"ns": ns}
            )
        if amount_node:
            amount = sign * float(amount_node[0].text)
        return amount

  
    def parse_entry_bgnr(self, ns, node):
        """Parse an Ntry node and yield transactions"""

        transaction = {
            "payment_ref": "/",
            "amount": 0,
            "narration": {},
            "transaction_type": {},
        }  # fallback defaults
        self.add_value_from_node(ns, node, "./ns:BookgDt/ns:Dt", transaction, "date")
        

        amount = self.parse_amount_bgnr(ns, node)
        if amount != 0.0:
            transaction["amount"] = amount

        self.add_value_from_node(
            ns,
            node,
            [
                "./ns:NtryDtls/ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref",
                "./ns:NtryDtls/ns:Btch/ns:PmtInfId",
                "./ns:NtryDtls/ns:TxDtls/ns:Refs/ns:AcctSvcrRef",
            ],
            transaction,
            "ref",
        )

        # enrich the notes with some more infos when they are available
        self.add_value_from_node(
            ns,
            node,
            "./ns:AddtlNtryInf",
            transaction["narration"],
            "%s (AddtlNtryInf)" % _("Additional Entry Information"),
        )
        self.add_value_from_node(
            ns,
            node,
            "./ns:RvslInd",
            transaction["narration"],
            "%s (RvslInd)" % _("Reversal Indicator"),
        )

        self.add_value_from_node(
            ns,
            node,
            "./ns:BkTxCd/ns:Domn/ns:Cd",
            transaction["transaction_type"],
            "Code",
        )
        self.add_value_from_node(
            ns,
            node,
            "./ns:BkTxCd/ns:Domn/ns:Fmly/ns:Cd",
            transaction["transaction_type"],
            "FmlyCd",
        )
        self.add_value_from_node(
            ns,
            node,
            "./ns:BkTxCd/ns:Domn/ns:Fmly/ns:SubFmlyCd",
            transaction["transaction_type"],
            "SubFmlyCd",
        )
        transaction["transaction_type"] = (
            "-".join(transaction["transaction_type"].values()) or ""
        )

        self.add_value_from_node(
            ns,
            node,
            ["./ns:NtryRef"],
            transaction["narration"],
            "%s (NtryRef)" % _("BG Reference"),
            join_str=" ",
        )
        
        self.add_value_from_node(
            ns,
            node,
            [
                "./ns:NtryRef",
            ],
            transaction,
            "payment_ref",
            join_str="\n",
        )
        
        
        
        


        cdtr_bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:CdtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        dbtr_bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:DbtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        if dbtr_bgnr_nodes:
            bgnr_nodes = dbtr_bgnr_nodes
        else:
            bgnr_nodes = cdtr_bgnr_nodes
        
        
        bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:CdtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        for bgnr_node in bgnr_nodes:
            is_bgnr = bgnr_node.xpath("./ns:SchmeNm/ns:Prtry", namespaces={"ns": ns})[0].text
            if is_bgnr != "BGNR":
                return
        if not bgnr_nodes:
            return
        
        self.generate_narration(transaction)

        yield transaction
        return




     
    
            
            
   
