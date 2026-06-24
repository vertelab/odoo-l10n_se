# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
import re
from datetime import datetime

from lxml import etree

from odoo import _, api, fields, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

# Swedish bank BIC → party identification scheme for the initiating party.
SCHEME_BY_BIC = {
    "init": {"BANK": {"SWEDSESS"}, "CUST": {"NDEASESS"}},
}


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _is_se_payment(self):
        self.ensure_one()
        return self.payment_method_id.code in (
            "se_credit_transfer",
            "se_credit_transfer_20",
        )

    def _mig_version(self):
        if self.payment_method_id.code == "se_credit_transfer_20":
            return "2.0"
        return ""

    def _se_scheme(self, party, bic):
        schemes = SCHEME_BY_BIC.get(party, {})
        for scheme, bics in schemes.items():
            if bic in bics:
                return scheme
        return "CUST" if party == "dbtr" else "BANK"

    def _se_pain_args(self):
        pain = self.payment_method_id.pain_version or "pain.001.001.03"
        if pain.startswith("pain.001.001.09"):
            return {"bic": "BICFI", "name_max": 140}
        return {"bic": "BIC", "name_max": 70}

    def _se_service_level(self):
        return "NURG"

    def _se_identifier(self):
        return (
            self.payment_mode_id.se_initiating_party_identifier
            or self.company_id.se_initiating_party_identifier
        )

    def _se_end_to_end(self, line):
        return line.se_end_to_end_id or str(line.id)

    def _se_corporate_pay_agreement_id(self):
        return (
            self.payment_mode_id.se_corporate_pay_agreement_id
            or self.company_id.se_corporate_pay_agreement_id
        )

    # -----------------------------------------------------------------
    # XML builders
    # -----------------------------------------------------------------

    def _x(self, parent, tag, text=None):
        elem = etree.SubElement(parent, tag)
        if text is not None:
            elem.text = text
        return elem

    def _xf(self, parent, tag, field_expr, eval_ctx, max_size, gen_args):
        val = self._prepare_field(tag, field_expr, eval_ctx, max_size, gen_args=gen_args)
        return self._x(parent, tag, val)

    def _build_initiating_party(self, parent, gen_args):
        bic = self.company_partner_bank_id.bank_id.bic or ""
        scheme = self._se_scheme("init", bic)
        party = self._x(parent, "InitgPty")
        if self._mig_version() == "2.0":
            name_max = gen_args.get("name_maxsize", 70)
            self._xf(party, "Nm", "self.company_partner_bank_id.partner_id.name",
                     {"self": self}, name_max, gen_args)
        identifier = self._se_identifier()
        if identifier:
            pid = self._x(party, "Id")
            oid = self._x(pid, "OrgId")
            oth = self._x(oid, "Othr")
            self._xf(oth, "Id", '"%s"' % identifier, {}, 35, gen_args)
            self._x(self._x(oth, "SchmeNm"), "Cd", scheme)

    def _build_debtor(self, parent, gen_args):
        partner = self.company_partner_bank_id.partner_id
        name_max = gen_args.get("name_maxsize", 140)

        if not partner.city:
            raise UserError(_(
                "City is required on the company's address for generating "
                "the payment file. The Town/City (TwnNm) field will be "
                "mandatory from November 2026.\n"
                "Please set a city on: %s"
            ) % partner.display_name)

        dbtr = self._x(parent, "Dbtr")
        self._xf(dbtr, "Nm", "self.company_partner_bank_id.partner_id.name",
                 {"self": self}, name_max, gen_args)

        if partner.country_id:
            pa = self._x(dbtr, "PstlAdr")
            if partner.street:
                self._x(pa, "StrtNm", partner.street)
            if partner.zip:
                self._x(pa, "PstCd", partner.zip)
            if partner.city:
                self._x(pa, "TwnNm", partner.city)
            self._x(pa, "Ctry", partner.country_id.code)

        cpa_id = self._se_corporate_pay_agreement_id()
        if cpa_id:
            did = self._x(dbtr, "Id")
            doid = self._x(did, "OrgId")
            doth = self._x(doid, "Othr")
            self._x(doth, "Id", cpa_id)
            self._x(self._x(doth, "SchmeNm"), "Cd", "BANK")

    def _creditor_address(self, partner, gen_args):
        if not partner.country_id:
            return None
        pa = etree.Element("PstlAdr")
        if partner.street:
            etree.SubElement(pa, "StrtNm").text = partner.street
        if partner.zip:
            etree.SubElement(pa, "PstCd").text = partner.zip
        if partner.city:
            etree.SubElement(pa, "TwnNm").text = partner.city
        etree.SubElement(pa, "Ctry").text = partner.country_id.code
        return pa

    def _build_creditor_block(self, parent, partner_bank, gen_args):
        partner = partner_bank.partner_id
        name_max = gen_args.get("name_maxsize", 140)

        if not partner.city:
            raise UserError(_(
                "City is required on the partner '%s' "
                "for generating the payment file. "
                "Town/City (TwnNm) will be mandatory from November 2026.\n"
                "Please open the partner form and set a city."
            ) % partner.display_name)

        cdtr = self._x(parent, "Cdtr")
        self._xf(cdtr, "Nm",
                 "(partner_bank.acc_holder_name or partner_bank.partner_id.name or '')",
                 {"partner_bank": partner_bank}, name_max, gen_args)
        addr = self._creditor_address(partner, gen_args)
        if addr is not None:
            cdtr.append(addr)

    def _build_agent(self, parent, prefix, partner_bank, gen_args):
        if not partner_bank.bank_bic:
            raise UserError(_(
                "BIC/Swift code is missing on the bank account '%s'. "
                "Please open Accounting > Configuration > Banks, "
                "select the bank linked to this account, and set its BIC."
            ) % partner_bank.display_name)
        ag = self._x(parent, "%sAgt" % prefix)
        fi = self._x(ag, "FinInstnId")
        self._x(fi, gen_args["bic_xml_tag"], partner_bank.bank_bic)
        if self._mig_version() == "2.0" and prefix == "Dbtr":
            pa = self._x(fi, "PstlAdr")
            self._x(pa, "Ctry",
                    partner_bank.partner_id.country_id.code or "SE")

    def _build_account(self, parent, prefix, partner_bank, currency=None):
        acct = self._x(parent, "%sAcct" % prefix)
        aid = self._x(acct, "Id")
        if partner_bank.acc_type == "iban":
            self._x(aid, "IBAN", partner_bank.sanitized_acc_number)
        else:
            self._x(aid, "Othr", partner_bank.sanitized_acc_number)
        if currency:
            self._x(acct, "Ccy", currency)

    # -----------------------------------------------------------------
    # Main generator
    # -----------------------------------------------------------------

    def generate_se_payment_file(self):
        self.ensure_one()
        pain = self.payment_method_id.pain_version or "pain.001.001.03"
        if not pain:
            raise UserError(
                _("No PAIN version is configured on the payment method. "
                  "Go to Invoicing > Configuration > Payment Methods, "
                  "select '%s', and set the PAIN version ("
                  "pain.001.001.03 or pain.001.001.09).")
                % self.payment_method_id.name
            )
        pa = self._se_pain_args()

        gen_args = {
            "bic_xml_tag": pa["bic"],
            "name_maxsize": pa["name_max"],
            "convert_to_ascii": self.payment_method_id.convert_to_ascii,
            "payment_method": "TRF",
            "file_prefix": "sct_se_",
            "pain_flavor": pain,
            "pain_xsd_file": self.payment_method_id.get_xsd_file_path(),
        }

        root = etree.Element(
            "Document",
            nsmap=self.generate_pain_nsmap(),
            attrib=self.generate_pain_attrib(),
        )
        cstmr = self._x(root, "CstmrCdtTrfInitn")

        # --- Group Header ---
        gh = self._x(cstmr, "GrpHdr")
        self._xf(gh, "MsgId", "self.name", {"self": self}, 35, gen_args)
        self._x(gh, "CreDtTm", datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
        nb_total = self._x(gh, "NbOfTxs")
        sum_total = self._x(gh, "CtrlSum")
        self._build_initiating_party(gh, gen_args)

        # Group lines by date
        by_date = {}
        for line in self.payment_line_ids:
            by_date.setdefault(line.date, []).append(line)

        txn = 0
        amt = 0.0

        for req_date, lines in sorted(by_date.items()):
            ds = fields.Date.to_string(req_date)
            pi = self._x(cstmr, "PmtInf")

            self._xf(pi, "PmtInfId", '"%s-%s"' % (self.name, ds.replace("-", "")),
                     {}, 35, gen_args)
            self._x(pi, "PmtMtd", "TRF")
            bic = self.company_partner_bank_id.bank_id.bic or ""
            if "SWEDSESS" not in bic:
                self._x(pi, "BtchBookg", str(self.batch_booking).lower())
            nb_grp = self._x(pi, "NbOfTxs")
            sum_grp = self._x(pi, "CtrlSum")

            pti = self._x(pi, "PmtTpInf")
            self._x(self._x(pti, "SvcLvl"), "Cd", self._se_service_level())

            red = self._x(pi, "ReqdExctnDt")
            if pain.startswith("pain.001.001.09"):
                self._x(red, "Dt", ds)
            else:
                red.text = ds

            self._build_debtor(pi, gen_args)
            self._build_account(pi, "Dbtr", self.company_partner_bank_id,
                                currency=lines[0].currency_id.name)
            self._build_agent(pi, "Dbtr", self.company_partner_bank_id, gen_args)
            if "SWEDSESS" not in bic:
                self._x(pi, "ChrgBr", self.charge_bearer or "SHAR")

            gn = 0
            gs = 0.0
            for line in lines:
                gn += 1
                gs += line.amount_currency

                if not line.partner_bank_id:
                    raise UserError(
                        _("No bank account set on the payment line for "
                          "partner '%s' (ref: %s).\n"
                          "Please open the partner form and add a bank "
                          "account with IBAN, then recreate the payment line.")
                        % (line.partner_id.name, line.name)
                    )

                cdt = self._x(pi, "CdtTrfTxInf")
                pid = self._x(cdt, "PmtId")
                self._xf(pid, "InstrId", "str(line.id)", {"line": line}, 35, gen_args)
                self._xf(pid, "EndToEndId", '"%s"' % self._se_end_to_end(line),
                         {}, 35, gen_args)

                amt_elem = self._x(cdt, "Amt")
                self._x(amt_elem, "InstdAmt", "%.2f" % line.amount_currency).set(
                    "Ccy", line.currency_id.name
                )

                self._build_agent(cdt, "Cdtr", line.partner_bank_id, gen_args)
                self._build_creditor_block(cdt, line.partner_bank_id, gen_args)
                self._build_account(cdt, "Cdtr", line.partner_bank_id)

                ref = line.communication or line.name or ""
                if ref:
                    ri = self._x(cdt, "RmtInf")
                    self._xf(ri, "Ustrd", '"%s"' % ref, {}, 140, gen_args)

            nb_grp.text = str(gn)
            sum_grp.text = "%.2f" % gs
            txn += gn
            amt += gs

        nb_total.text = str(txn)
        sum_total.text = "%.2f" % amt

        return self.finalize_sepa_file_creation(root, gen_args)

    # -----------------------------------------------------------------
    # Hooks
    # -----------------------------------------------------------------

    def generate_payment_file(self):
        self.ensure_one()
        if self._is_se_payment():
            identifier = self._se_identifier()
            if not identifier:
                raise UserError(
                    _("Missing Initiating Party Signer ID for Swedish "
                      "Credit Transfer.\n"
                      "Go to Invoicing > Configuration > Payment Modes, "
                      "select your SE payment mode, and fill in the "
                      "'SE Initiating Party Identifier' field with the "
                      "ID from your bank agreement.")
                )
            version = self._mig_version()
            if version == "2.0":
                if not re.match(r"^\d{9}ORI\d{4}$", identifier):
                    raise UserError(_(
                        "Invalid Initiating Party Signer ID format for "
                        "Swedbank MIG 2.0. The format must be "
                        "nnnnnnnnnORInnnn (e.g. 012345678ORI0001). "
                        "Current value: %s"
                    ) % identifier)
                cpa_id = self._se_corporate_pay_agreement_id()
                if cpa_id and not re.match(r"^\d{9}CPO\d{4}$", cpa_id):
                    raise UserError(_(
                        "Invalid Corporate Pay Agreement ID format for "
                        "Swedbank MIG 2.0. The format must be "
                        "nnnnnnnnnCPOnnnn (e.g. 123456789CPO0001). "
                        "Current value: %s"
                    ) % cpa_id)
            elif not version:
                if not re.match(r"^[A-Z0-9]{9,35}$", identifier):
                    raise UserError(_(
                        "Invalid Initiating Party Identifier format. "
                        "Expected 9-35 alphanumeric characters (A-Z, 0-9). "
                        "Current value: %s"
                    ) % identifier)
            return self.generate_se_payment_file()
        return super().generate_payment_file()
