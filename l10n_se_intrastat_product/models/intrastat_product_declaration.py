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
        """Generate the SCB EDAS Intrastat XML file.

        NOTE: the schema used here is the SCB EDAS Intrastat format, NOT the
        Swedish Customs (Tullverket) WCO declaration schema. The previous
        implementation emitted the customs schema, which SCB cannot read.
        The element names below must be verified against the current SCB
        "Intrastat - teknisk beskrivning" before the file is sent in.
        """
        self.ensure_one()
        company = self.company_id
        partner = company.partner_id

        decl_date = fields.Date.context_today(self)

        root = etree.Element("IntrastatDeclaration")

        # Reporting period and flow
        etree.SubElement(root, "Period").text = f"{self.year}{int(self.month):02d}"
        etree.SubElement(root, "Flow").text = (
            "Arrivals" if self.declaration_type == "arrivals" else "Dispatches"
        )

        # Declaring party
        etree.SubElement(root, "ReportingEntityId").text = self._se_clean_org_nr()
        etree.SubElement(root, "ReportingEntityName").text = company.name
        if company.intrastat_contact_name:
            etree.SubElement(root, "ContactPersonName").text = (
                company.intrastat_contact_name
            )
        if company.intrastat_contact_phone:
            etree.SubElement(root, "ContactPersonPhone").text = (
                company.intrastat_contact_phone
            )
        if company.intrastat_contact_email:
            etree.SubElement(root, "ContactPersonEmail").text = (
                company.intrastat_contact_email
            )

        # Submission metadata
        etree.SubElement(root, "DeclarationId").text = self._se_generate_declaration_id()
        etree.SubElement(root, "SubmissionDate").text = decl_date.isoformat()
        etree.SubElement(root, "ActionCode").text = (self.action or "replace").upper()
        etree.SubElement(root, "RevisionNumber").text = str(self.revision)

        # Country of consignment / destination is the partner country per line
        etree.SubElement(root, "CountryOfOrigin").text = "SE"

        # Declaration lines
        items = etree.SubElement(root, "Items")
        for decl_line in self.declaration_line_ids:
            item = etree.SubElement(items, "Item")

            etree.SubElement(item, "SequenceNumber").text = str(
                decl_line.line_number
            )

            # Commodity code (CN8)
            etree.SubElement(item, "CommodityCode").text = self._se_get_cn_code(
                decl_line
            )

            # Partner member state
            etree.SubElement(item, "PartnerCountry").text = (
                decl_line.src_dest_country_code or ""
            )

            # Country of origin (arrivals only, extended reporting)
            if decl_line.product_origin_country_code:
                etree.SubElement(item, "CountryOfOrigin").text = (
                    decl_line.product_origin_country_code
                )

            # Nature of transaction (EU two-digit code, e.g. "11")
            etree.SubElement(item, "NatureOfTransaction").text = (
                self._se_get_transaction_code(decl_line)
            )

            # Transport mode
            if decl_line.transport_id:
                etree.SubElement(item, "ModeOfTransport").text = (
                    decl_line.transport_id.code or "9"
                )

            # Region of origin / destination (län) — company default,
            # since the declaration line has no region field of its own.
            if company.intrastat_region_id:
                etree.SubElement(item, "RegionOfOrigin").text = (
                    company.intrastat_region_id.code
                )

            # Statistical value in SEK, whole kronor, no currency element
            etree.SubElement(item, "StatisticalValue").text = "{:.0f}".format(
                decl_line.amount_company_currency
            )

            # Net mass in kg, with decimals
            etree.SubElement(item, "NetMass").text = "{:.3f}".format(
                decl_line.weight or 0.0
            )

            # Supplementary units
            if decl_line.intrastat_unit_id and decl_line.suppl_unit_qty:
                etree.SubElement(item, "SupplementaryQuantity").text = str(
                    decl_line.suppl_unit_qty
                )
                etree.SubElement(item, "SupplementaryUnit").text = (
                    decl_line.intrastat_unit_id.name or ""
                )

            # Partner VAT number (dispatches)
            if self.declaration_type == "dispatches" and decl_line.vat:
                etree.SubElement(item, "PartnerVatNumber").text = decl_line.vat

        tree = etree.ElementTree(root)
        xml_bytes = BytesIO()
        tree.write(
            xml_bytes,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True,
        )
        return xml_bytes.getvalue()

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

