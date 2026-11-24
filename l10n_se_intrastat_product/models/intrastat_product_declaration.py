# -*- coding: utf-8 -*-
# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import date
from io import BytesIO
from lxml import etree
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError

_logger = logging.getLogger(__name__)

# Swedish country code mappings (same as EU base)
SRC_DEST_COUNTRY_CODE_MAPPING = {
    "GB": "XI",
    "GR": "EL",
}
PRODUCT_ORIGIN_COUNTRY_CODE_MAPPING = {
    "GB": "XU",
    "GR": "EL",
}


class IntrastatProductDeclaration(models.Model):
    _inherit = "intrastat.product.declaration"

    swedish_declaration_id = fields.Char(
        string="SCB Declaration ID",
        help="Identifier assigned by SCB for this declaration.",
        readonly=True,
    )

    # ----------------------------------------------------------
    # Swedish-specific invoice domain
    # ----------------------------------------------------------

    def _prepare_invoice_domain(self):
        """Swedish Intrastat: filter on invoice date (fakturadatum) instead of account.move date.
        Also include triangular trade (trepartshandel) transactions.
        Falls back to accounting date (date) for entries where invoice_date is not set.
        """
        start_date = date(int(self.year), int(self.month), 1)
        end_date = start_date + relativedelta(day=1, months=+1, days=-1)
        domain = [
            "|",
            ("invoice_date", ">=", start_date),
            ("date", ">=", start_date),
            "|",
            ("invoice_date", "<=", end_date),
            ("date", "<=", end_date),
            ("state", "=", "posted"),
            ("intrastat_fiscal_position", "in", ("b2b", "b2c")),
            ("company_id", "=", self.company_id.id),
        ]
        if self.declaration_type == "arrivals":
            domain.append(("move_type", "in", ("in_invoice", "in_refund")))
        elif self.declaration_type == "dispatches":
            domain.append(("move_type", "in", ("out_invoice", "out_refund")))
        return domain

    # ----------------------------------------------------------
    # Swedish reporting rules
    # ----------------------------------------------------------

    def _check_se_period(self):
        """SCB collects Intrastat monthly — a declaration covers one calendar
        month. Reject anything else before lines are gathered.
        """
        self.ensure_one()
        if not self.year or not self.month:
            raise UserError(
                _("Both year and month must be set on the Intrastat declaration.")
            )
        try:
            month = int(self.month)
        except (TypeError, ValueError):
            raise UserError(
                _("The month '%(month)s' is not a valid month.", month=self.month)
            )
        if not 1 <= month <= 12:
            raise UserError(
                _("The month '%(month)s' is not a valid month.", month=self.month)
            )

    def action_gather(self):
        """Validate the reporting period before gathering invoice lines."""
        self._check_se_period()
        return super().action_gather()

    def draft2confirmed(self):
        """Validate the reporting period before generating declaration lines."""
        self._check_se_period()
        return super().draft2confirmed()

    def _gather_invoices(self, notedict):
        """Swedish override: accessory costs are always included.

        The OCA base reads company_id.intrastat_accessory_costs and, when that
        flag is off, silently skips the freight/packaging/insurance lines
        instead of folding them into the statistical value. In Sweden that is
        not optional — the statistical value is the market value of the goods
        at the Swedish border, delivery costs included (SCB Handledning 2026,
        section 7).

        The flag is a stored user setting on res.company. The Swedish rule has
        no "off" position, so it is switched on here when it has been turned
        off, and stays on. The post_init_hook sets it on install so this is
        normally a no-op.
        """
        if not self.company_id.intrastat_accessory_costs:
            self.company_id.intrastat_accessory_costs = True
        return super()._gather_invoices(notedict)

    def _handle_invoice_accessory_cost(
        self,
        invoice,
        lines_current_invoice,
        total_inv_accessory_costs_cc,
        total_inv_product_cc,
        total_inv_weight,
    ):
        """Distribute accessory costs pro-rata over the goods lines.

        Only services flagged is_accessory_cost (freight, packaging,
        insurance) reach this method — see _gather_invoices. A service that is
        NOT flagged (consulting, travel, rebates, ...) is never part of the
        goods value and must not be reported to Intrastat at all.
        """
        if not total_inv_accessory_costs_cc or not lines_current_invoice:
            return

        if total_inv_product_cc:
            # pro-rata of the value
            for ac_line_vals in lines_current_invoice:
                ac_line_vals["amount_accessory_cost_company_currency"] = (
                    total_inv_accessory_costs_cc
                    * ac_line_vals["amount_company_currency"]
                    / total_inv_product_cc
                )
        elif total_inv_weight:
            # pro-rata of the weight
            for ac_line_vals in lines_current_invoice:
                ac_line_vals["amount_accessory_cost_company_currency"] = (
                    total_inv_accessory_costs_cc
                    * ac_line_vals["weight"]
                    / total_inv_weight
                )
        else:
            for ac_line_vals in lines_current_invoice:
                ac_line_vals["amount_accessory_cost_company_currency"] = (
                    total_inv_accessory_costs_cc / len(lines_current_invoice)
                )

    # ----------------------------------------------------------
    # Swedish region codes (län)
    # ----------------------------------------------------------

    def _get_region_code(self, inv_line, notedict):
        """Return the Swedish län code for a declaration line.

        The OCA base implementation already resolves the region from the
        stock location / warehouse and falls back to the company default,
        so the Swedish override only needs to return the code.
        """
        self.ensure_one()
        region = self._get_region(inv_line, notedict)
        if region:
            return region.code
        if self.company_id.intrastat_region_id:
            return self.company_id.intrastat_region_id.code
        return False

    # ----------------------------------------------------------
    # Prepare Swedish EDAS XML for SCB
    # ----------------------------------------------------------

    def _check_generate_xml(self):
        """Add Swedish-specific checks."""
        super()._check_generate_xml()
        if not self.company_id.intrastat_contact_email:
            raise UserError(
                _("Intrastat Contact Email is not set for company '%s'. "
                  "Configure it in Accounting → Configuration → Settings → Intrastat.")
                % self.company_id.name
            )

    def _generate_xml(self):
        """Generate the SCB Intrastat XML file (INSTAT/XML version 6.2).

        Format: INSTAT/XML 6.2, the Eurostat Message Implementation Guideline
        that SCB uses for Intrastat file transfer. The schema is instat62.xsd
        and the envelope/declaration/item structure below follows it.

        Reference: SCB "Bilaga 1: Riktlinjer for implementering av XML i
        Intrastat" (static/spec/ in this module).

        Note that SCB only accepts files from software certified by SCB
        (Bilaga 2). Generating a well-formed file is not the same as being
        cleared for submission.
        """
        self.ensure_one()
        company = self.company_id
        partner = company.partner_id

        now = fields.Datetime.now()
        org_nr = self._se_clean_org_nr()

        root = etree.Element("INSTAT")
        envelope = etree.SubElement(root, "Envelope")

        # --- Envelope -------------------------------------------------
        etree.SubElement(envelope, "envelopeId").text = self._se_envelope_id()

        dt = etree.SubElement(envelope, "DateTime")
        etree.SubElement(dt, "date").text = now.date().isoformat()
        etree.SubElement(dt, "time").text = now.strftime("%H:%M:%S")

        # Sender: the declaring party (PSI = Party responsible for providing
        # Statistical Information).
        sender = etree.SubElement(envelope, "Party", partyType="PSI", partyRole="sender")
        etree.SubElement(sender, "partyId").text = org_nr
        etree.SubElement(sender, "partyName").text = company.name
        if company.intrastat_contact_name or company.intrastat_contact_email:
            contact = etree.SubElement(sender, "ContactPerson")
            etree.SubElement(contact, "contactPersonName").text = (
                company.intrastat_contact_name or company.name
            )
            if company.intrastat_contact_phone or company.intrastat_contact_email:
                caddr = etree.SubElement(contact, "Address")
                if company.intrastat_contact_phone:
                    etree.SubElement(caddr, "phoneNumber").text = (
                        company.intrastat_contact_phone
                    )
                if company.intrastat_contact_email:
                    etree.SubElement(caddr, "e-mail").text = (
                        company.intrastat_contact_email
                    )

        # Receiver: the collecting centre (SCB).
        receiver = etree.SubElement(
            envelope, "Party", partyType="CC", partyRole="receiver"
        )
        etree.SubElement(receiver, "partyId").text = "SCB"
        etree.SubElement(receiver, "partyName").text = (
            "Statistiska centralbyran (SCB)"
        )

        etree.SubElement(envelope, "softwareUsed").text = (
            "SW=Odoo;l10n_se_intrastat_product;OS=Linux"
        )

        # --- Declaration ----------------------------------------------
        decl = etree.SubElement(envelope, "Declaration")
        etree.SubElement(decl, "declarationId").text = self._se_generate_declaration_id()
        etree.SubElement(decl, "referencePeriod").text = (
            f"{self.year}-{int(self.month):02d}"
        )
        etree.SubElement(decl, "PSIId").text = org_nr

        function = etree.SubElement(decl, "Function")
        etree.SubElement(function, "functionCode").text = self._se_function_code()

        # 1 = full (detailed) declaration, 2 = simplified
        etree.SubElement(decl, "declarationTypeCode").text = (
            "1" if self.reporting_level == "extended" else "2"
        )

        # A = arrival, D = dispatch
        etree.SubElement(decl, "flowCode").text = (
            "A" if self.declaration_type == "arrivals" else "D"
        )
        etree.SubElement(decl, "currencyCode").text = "SEK"

        # Declaration totals. instat62.xsd fixes the order:
        # totalNetMass, totalInvoicedAmount, totalStatisticalValue, Item*,
        # totalNumberLines, totalNumberDetailedLines.
        etree.SubElement(decl, "totalNetMass").text = str(
            int(round(sum(self.declaration_line_ids.mapped("weight"))))
        )
        etree.SubElement(decl, "totalStatisticalValue").text = "{:.2f}".format(
            sum(self.declaration_line_ids.mapped("amount_company_currency"))
        )

        # --- Items ----------------------------------------------------
        for decl_line in self.declaration_line_ids:
            item = etree.SubElement(decl, "Item")
            etree.SubElement(item, "itemNumber").text = str(decl_line.line_number)

            cn8 = etree.SubElement(item, "CN8")
            etree.SubElement(cn8, "CN8Code").text = self._se_get_cn_code(decl_line)
            if decl_line.intrastat_unit_id:
                etree.SubElement(cn8, "SUCode").text = (
                    decl_line.intrastat_unit_id.name or ""
                )

            # Partner member state
            etree.SubElement(item, "MSConsDestCode").text = (
                decl_line.src_dest_country_code or ""
            )

            # Country of origin — arrivals only per the MIG
            if (
                self.declaration_type == "arrivals"
                and decl_line.product_origin_country_code
            ):
                etree.SubElement(item, "countryOfOriginCode").text = (
                    decl_line.product_origin_country_code
                )

            # netMass is xsd:integer in instat62.xsd — whole kilograms
            etree.SubElement(item, "netMass").text = str(
                int(round(decl_line.weight or 0.0))
            )

            if decl_line.intrastat_unit_id and decl_line.suppl_unit_qty:
                etree.SubElement(item, "quantityInSU").text = str(
                    int(round(decl_line.suppl_unit_qty))
                )

            etree.SubElement(item, "statisticalValue").text = "{:.2f}".format(
                decl_line.amount_company_currency
            )

            nature = etree.SubElement(item, "NatureOfTransaction")
            etree.SubElement(nature, "natureOfTransactionACode").text = (
                self._se_get_transaction_code(decl_line)
            )

            if decl_line.transport_id:
                etree.SubElement(item, "modeOfTransportCode").text = (
                    decl_line.transport_id.code or "9"
                )

            if company.intrastat_region_id:
                etree.SubElement(item, "regionCode").text = (
                    company.intrastat_region_id.code
                )

            if decl_line.vat:
                etree.SubElement(item, "partnerId").text = decl_line.vat

        etree.SubElement(decl, "totalNumberLines").text = str(
            len(self.declaration_line_ids)
        )
        etree.SubElement(decl, "totalNumberDetailedLines").text = str(
            len(self.computation_line_ids)
        )

        etree.SubElement(envelope, "numberOfDeclarations").text = "1"

        # ISO 8859-1 is what SCB specifies for the character representation.
        xml_bytes = BytesIO()
        etree.ElementTree(root).write(
            xml_bytes,
            encoding="ISO-8859-1",
            xml_declaration=True,
            pretty_print=True,
        )
        return xml_bytes.getvalue()

    def _se_envelope_id(self):
        """Envelope identifier, AA followed by a sequence number."""
        return "AA{:06d}".format(self.id or 0)

    def _se_function_code(self):
        """Map the OCA declaration action onto the INSTAT functionCode.

        O = original, N = nil return, D = delete, R = replace, M = modify.
        """
        mapping = {
            "replace": "R",
            "append": "O",
            "nihil": "N",
            "delete": "D",
        }
        return mapping.get(self.action or "", "O")

    def _se_get_cn_code(self, decl_line):
        """Return the 8-digit CN commodity code, padded if short."""
        if decl_line.hs_code_id:
            hs_code = (
                decl_line.hs_code_id.local_code
                or decl_line.hs_code_id.code
                or "99999999"
            )
        else:
            hs_code = "99999999"
        if len(hs_code) < 8:
            hs_code = hs_code.ljust(8, "0")
        return hs_code[:8]

    def _se_clean_org_nr(self):
        """Return the Swedish organisation number without prefix/separators."""
        org_nr = self.company_id.partner_id.vat or ""
        return (
            org_nr.replace("SE", "")
            .replace("-", "")
            .replace(" ", "")
            .strip()
        )

    def _se_get_period_end(self):
        """Get the last day of the declaration period."""
        start = date(int(self.year), int(self.month), 1)
        end = start + relativedelta(day=1, months=+1, days=-1)
        return end.isoformat()

    def _se_generate_declaration_id(self):
        """Generate unique SCB declaration ID."""
        org_nr = self.company_id.partner_id.vat or "0000000000"
        org_nr_clean = org_nr.replace("SE", "").replace("-", "").replace(" ", "")[:10]
        decl_type = "I" if self.declaration_type == "arrivals" else "U"
        return f"{decl_type}{self.year}{self.month}{org_nr_clean}"

    def _se_get_transaction_code(self, decl_line):
        """Return the EU nature-of-transaction code for SCB.

        The OCA intrastat.transaction codes ARE the EU two-digit codes
        (11, 12, 21 ... 99) that SCB expects, so they are passed through
        unchanged. The previous implementation remapped them onto a
        non-existent single/double-digit Swedish scheme and produced
        invalid codes such as "82" for anything it did not recognise.
        """
        transaction = decl_line.transaction_id
        if not transaction or not transaction.code:
            return "11"  # B2B sale/purchase is the normal case
        return transaction.code

