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

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"
    bgnr_ref = fields.Char("Bank Giro Referens", help="Used to divide bankgiro into seperate bankstatments")

class CamtParser(models.AbstractModel):
    _inherit = "account.statement.import.camt.parser"
    
    
    def get_bank_giro_account(self, ns, node):
        is_bgnr_account = False
        sign_node = node.xpath("ns:CdtDbtInd", namespaces={"ns": ns}) 
        if not sign_node:
            sign_node = node.xpath("../../ns:CdtDbtInd", namespaces={"ns": ns})
        if sign_node and sign_node[0].text == "CRDT":
            bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:CdtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        else:
            bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:DbtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        for bgnr_node in bgnr_nodes:
            is_bgnr = bgnr_node.xpath("./ns:SchmeNm/ns:Prtry", namespaces={"ns": ns})
            if is_bgnr[0].text != "BGNR":
                continue
                
            if is_bgnr_account and is_bgnr_account != bgnr_node.xpath("./ns:Id", namespaces={"ns": ns})[0].text:
                raise UserError(f'There are deposits for different bankgiro accounts. {is_bgnr_account} {bgnr_node.xpath("./ns:Id", namespaces={"ns": ns})[0].text}')
            is_bgnr_account = bgnr_node.xpath("./ns:Id", namespaces={"ns": ns})[0].text
        return is_bgnr_account
        

    def parse_transaction_details_bgnr(self, ns, node, transaction):
        """Parse TxDtls node."""
        # message
        self.add_value_from_node(
            ns,
            node,
            [
                "./ns:RmtInf/ns:Ustrd|./ns:RtrInf/ns:AddtlInf",
                "./ns:AddtlNtryInf",
                "./ns:Refs/ns:InstrId",
            ],
            transaction,
            "payment_ref",
            join_str="\n",
        )

        self.add_value_from_node(
            ns,
            node,
            ["./ns:RmtInf/ns:Ustrd"],
            transaction["narration"],
            "%s (RmtInf/Ustrd)" % _("Unstructured Reference"),
            join_str=" ",
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref"],
            transaction["narration"],
            "%s (RmtInf/Strd/CdtrRefInf/Ref)" % _("Structured Reference"),
            join_str=" ",
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:AddtlTxInf"],
            transaction["narration"],
            "%s (AddtlTxInf)" % _("Additional Transaction Information"),
            join_str=" ",
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:RtrInf/ns:Rsn/ns:Cd"],
            transaction["narration"],
            "%s (RtrInf/Rsn/Cd)" % _("Return Reason Code"),
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:RtrInf/ns:Rsn/ns:Cd"],
            transaction["narration"],
            "%s (RtrInf/Rsn/Prtry)" % _("Return Reason Code (Proprietary)"),
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:RtrInf/ns:AddtlInf"],
            transaction["narration"],
            "%s (RtrInf/AddtlInf)" % _("Return Reason Additional Information"),
            join_str=" ",
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:Refs/ns:MsgId"],
            transaction["narration"],
            "%s (Refs/MsgId)" % _("Msg Id"),
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:Refs/ns:AcctSvcrRef"],
            transaction["narration"],
            "%s (Refs/AcctSvcrRef)" % _("Account Servicer Reference"),
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:Refs/ns:EndToEndId"],
            transaction["narration"],
            "%s (Refs/EndToEndId)" % _("End To End Id"),
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:Refs/ns:InstrId"],
            transaction["narration"],
            "%s (Refs/InstrId)" % _("Instructed Id"),
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:Refs/ns:TxId"],
            transaction["narration"],
            "%s (Refs/TxId)" % _("Transaction Identification"),
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:Refs/ns:MntId"],
            transaction["narration"],
            "%s (Refs/MntId)" % _("Mandate Id"),
        )
        self.add_value_from_node(
            ns,
            node,
            ["./ns:Refs/ns:ChqNb"],
            transaction["narration"],
            "%s (Refs/ChqNb)" % _("Cheque Number"),
        )

        self.add_value_from_node(
            ns, node, ["./ns:AddtlTxInf"], transaction, "payment_ref", join_str="\n"
        )
        # eref
        self.add_value_from_node(
            ns,
            node,
            [
                "./ns:RmtInf/ns:Strd/ns:CdtrRefInf/ns:Ref",
                "./ns:Refs/ns:EndToEndId",
                "./ns:Ntry/ns:AcctSvcrRef",
            ],
            transaction,
            "ref",
        )
        amount = self.parse_amount_bgnr(ns, node)
        if amount != 0.0:
            transaction["amount"] = amount
        # remote party values
        party_type = "Dbtr"
        party_type_node = node.xpath("../../ns:CdtDbtInd", namespaces={"ns": ns})
        if party_type_node and party_type_node[0].text != "CRDT":
            party_type = "Cdtr"
        party_node = node.xpath(
            "./ns:RltdPties/ns:%s" % party_type, namespaces={"ns": ns}
        )
        if party_node:
            name_node = node.xpath(
                "./ns:RltdPties/ns:{pt}/ns:Nm | ./ns:RltdPties/ns:{pt}/ns:Pty/ns:Nm".format(
                    pt=party_type
                ),
                namespaces={"ns": ns},
            )
            if name_node:
                transaction["partner_name"] = name_node[0].text
            else:
                self.add_value_from_node(
                    ns,
                    party_node[0],
                    "./ns:PstlAdr/ns:AdrLine",
                    transaction,
                    "partner_name",
                )
            self.add_value_from_node(
                ns,
                party_node[0],
                "./ns:PstlAdr/ns:StrtNm|"
                "./ns:PstlAdr/ns:BldgNb|"
                "./ns:PstlAdr/ns:BldgNm|"
                "./ns:PstlAdr/ns:PstBx|"
                "./ns:PstlAdr/ns:PstCd|"
                "./ns:PstlAdr/ns:TwnNm|"
                "./ns:PstlAdr/ns:TwnLctnNm|"
                "./ns:PstlAdr/ns:DstrctNm|"
                "./ns:PstlAdr/ns:CtrySubDvsn|"
                "./ns:PstlAdr/ns:Ctry|"
                "./ns:PstlAdr/ns:AdrLine",
                transaction["narration"],
                "%s (PstlAdr)" % _("Postal Address"),
                join_str=" | ",
            )
        # Get remote_account from iban or from domestic account:
        account_node = node.xpath(
            "./ns:RltdPties/ns:%sAcct/ns:Id" % party_type, namespaces={"ns": ns}
        )
        if account_node:
            iban_node = account_node[0].xpath("./ns:IBAN", namespaces={"ns": ns})
            if iban_node:
                transaction["account_number"] = iban_node[0].text
            else:
                self.add_value_from_node(
                    ns,
                    account_node[0],
                    "./ns:Othr/ns:Id",
                    transaction,
                    "account_number",
                )
    
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
            # ~ _logger.warning(f"{statement=}")
            if len(statement["transactions"]):
                if "currency" in statement:
                    currency = statement.pop("currency")
                if "account_number" in statement:
                    account_number = statement.pop("account_number")
                # ~ _logger.warning(f"{statement=}")
                statements.append(statement)
        # ~ _logger.warning(f"{currency=}")
        # ~ _logger.warning(f"{account_number=}")
        # ~ _logger.warning(f"{statements=}")
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
        
        
        sign_node = node.xpath("ns:CdtDbtInd", namespaces={"ns": ns}) 
        if not sign_node:
            sign_node = node.xpath("../../ns:CdtDbtInd", namespaces={"ns": ns})
        if sign_node and sign_node[0].text == "CRDT":
            bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:CdtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        else:
            bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:DbtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        
        self.add_value_from_node(
            ns,
            node,
            [
                "./ns:NtryRef",
            ],
            transaction,
            "bgnr_ref",
            join_str="\n",
        )
        
        bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:CdtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        for bgnr_node in bgnr_nodes:
            is_bgnr = bgnr_node.xpath("./ns:SchmeNm/ns:Prtry", namespaces={"ns": ns})[0].text
            if is_bgnr != "BGNR":
                return
        if not bgnr_nodes:
            return
            
        details_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls", namespaces={"ns": ns})
        if len(details_nodes) == 0:
            self.generate_narration(transaction)
            
            res_partner = self.env['res.partner'].search([('name','=',transaction.get('partner_name'))], limit=1)
            _logger.warning(f"{res_partner=}")
            if not res_partner:
                res_partner = self.env['res.partner'].create({'name':transaction.get('partner_name')})
                _logger.warning(f"{res_partner=}")
            transaction['partner_id'] = res_partner.id
            
            yield transaction
            return
            
        transaction_base = transaction
        for node in details_nodes:
            transaction = transaction_base.copy()
            self.parse_transaction_details_bgnr(ns, node, transaction)
            self.generate_narration(transaction)
            
            res_partner = self.env['res.partner'].search([('name','=',transaction.get('partner_name'))], limit=1)
            _logger.warning(f"{res_partner=}")
            if not res_partner:
                res_partner = self.env['res.partner'].create({'name':transaction.get('partner_name'),'company_type': 'company'})
                _logger.warning(f"{res_partner=}")
            transaction['partner_id'] = res_partner.id
            
            yield transaction
            

    def parse_entry(self, ns, node):
        # ~ res = super(CamtParser, self).parse_entry(ns, node)
        
        """Parse an Ntry node and yield transactions"""
        transaction = {
            "payment_ref": "/",
            "amount": 0,
            "narration": {},
            "transaction_type": {},
        }  # fallback defaults
        self.add_value_from_node(ns, node, "./ns:BookgDt/ns:Dt", transaction, "date")
        amount = self.parse_amount(ns, node)
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
        
        ##ADDITIONS to handlde bgnr nodes
        bgnr_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls/ns:RltdPties/ns:CdtrAcct/ns:Id/ns:Othr", namespaces={"ns": ns})
        for bgnr_node in bgnr_nodes:
            is_bgnr = bgnr_node.xpath("./ns:SchmeNm/ns:Prtry", namespaces={"ns": ns})[0].text
            if is_bgnr == "BGNR":
                
                details_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls", namespaces={"ns": ns})
                
                if len(details_nodes) == 0:
                    self.generate_narration(transaction)
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
                    yield transaction
                    return
                else:
                    general_tansaction = transaction.copy()
                    self.generate_narration(general_tansaction)
                    general_tansaction['narration'] = "                         General Narration \n" + general_tansaction['narration'] + "\n\n                         Detailed Narration \n"
                    transaction_base = transaction
                    for node in details_nodes:
                        transaction = transaction_base.copy()
                        self.parse_transaction_details(ns, node, transaction)
                        self.generate_narration(transaction)
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
                    general_tansaction['narration'] = general_tansaction['narration'] + transaction['narration'] + "\n"
                    yield general_tansaction
                    return
                

        ##ADDITIONS

        details_nodes = node.xpath("./ns:NtryDtls/ns:TxDtls", namespaces={"ns": ns})
        if len(details_nodes) == 0:
            self.generate_narration(transaction)
            yield transaction
            return
        transaction_base = transaction
        for node in details_nodes:
            transaction = transaction_base.copy()
            self.parse_transaction_details(ns, node, transaction)
            self.generate_narration(transaction)
            yield transaction
