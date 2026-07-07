# -*- coding: utf-8 -*-
# Copyright 2026 Vertel AB (https://vertel.se)
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
        """Override to use Swedish län codes.
        Falls back to company's default Intrastat region if not found.
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
        """Generate Swedish EDAS XML for SCB Intrastat submission."""
        self.ensure_one()
        company = self.company_id
        partner = company.partner_id
        country_code = partner.country_id.code or "SE"

        decl_date = fields.Date.context_today(self)

        # Create root element
        nsmap = {
            None: "urn:se:customs:datamodel:WCO:Declaration:1",
            "ns2": "urn:se:customs:datamodel:WCO:DS:1",
        }
        root = etree.Element(
            "Declaration",
            nsmap=nsmap,
        )

        # Functionary (declaring party)
        functionary = etree.SubElement(root, "Functionary")
        etree.SubElement(functionary, "FunctionaryCode").text = self._se_get_functionary_code()

        # Declaration office
        decl_office = etree.SubElement(root, "DeclarationOffice")
        etree.SubElement(decl_office, "ID").text = self._se_get_office_code()

        # Agent (company)
        agent = etree.SubElement(root, "Agent")
        etree.SubElement(agent, "ID").text = partner.vat or ""
        etree.SubElement(agent, "Name").text = company.name

        # Contact person
        if company.intrastat_contact_name:
            etree.SubElement(agent, "ContactName").text = company.intrastat_contact_name
        if company.intrastat_contact_phone:
            etree.SubElement(agent, "ContactPhone").text = company.intrastat_contact_phone
        if company.intrastat_contact_email:
            etree.SubElement(agent, "ContactEmail").text = company.intrastat_contact_email

        # Declaration period
        decl_info = etree.SubElement(root, "DeclarationInfo")
        etree.SubElement(decl_info, "DeclarationType").text = self._se_get_declaration_type_code()

        # Reference period
        ref_period = etree.SubElement(decl_info, "ReferencePeriod")
        period_start = f"{self.year}-{self.month}-01"
        etree.SubElement(ref_period, "StartDate").text = period_start
        etree.SubElement(ref_period, "EndDate").text = self._se_get_period_end()

        # Flow direction
        flow = "IMPORT" if self.declaration_type == "arrivals" else "EXPORT"
        etree.SubElement(decl_info, "FlowDirection").text = flow

        # Submission
        etree.SubElement(decl_info, "SubmissionDate").text = decl_date.isoformat()
        etree.SubElement(decl_info, "DeclarationID").text = self._se_generate_declaration_id()

        # Action (replace/append/nihil)
        etree.SubElement(decl_info, "ActionCode").text = self.action.upper()
        etree.SubElement(decl_info, "RevisionNumber").text = str(self.revision)

        # Declaration lines
        goods_shipment = etree.SubElement(root, "GoodsShipment")
        etree.SubElement(goods_shipment, "ConsignmentCountry").text = country_code

        # Trading country (always the other EU country for Intrastat)
        for decl_line in self.declaration_line_ids:
            consignment = etree.SubElement(goods_shipment, "Consignment")

            # Line number
            etree.SubElement(consignment, "SequenceNumeric").text = str(decl_line.line_number)

            # Goods item
            goods_item = etree.SubElement(consignment, "GoodsItem")

            # Commodity code (taric)
            classification = etree.SubElement(goods_item, "Classification")
            ident = etree.SubElement(classification, "Identification")
            if decl_line.hs_code_id:
                hs_code = decl_line.hs_code_id.local_code or decl_line.hs_code_id.code or "99999999"
            else:
                hs_code = "99999999"
            # Pad to 8 digits for CN code
            if len(hs_code) < 8:
                hs_code = hs_code.ljust(8, "0")
            etree.SubElement(ident, "ID").text = hs_code[:8]

            # Country of origin/destination
            country_code_val = decl_line.src_dest_country_code or ""
            if country_code_val == "XI":
                country_code_val = "XI"  # Northern Ireland (post-Brexit)
            etree.SubElement(consignment, "ConsigneeCountry").text = country_code_val
            etree.SubElement(consignment, "ConsignorCountry").text = country_code_val

            # Statistical value (in SEK)
            value = etree.SubElement(goods_item, "StatisticalValue")
            amount_sek = "{:.0f}".format(decl_line.amount_company_currency)
            etree.SubElement(value, "Amount").text = amount_sek
            etree.SubElement(value, "CurrencyCode").text = "SEK"

            # Net mass
            measure = etree.SubElement(goods_item, "GoodsMeasure")
            etree.SubElement(measure, "NetWeightMeasure").text = "{:.0f}".format(decl_line.weight)

            # Supplementary units
            if decl_line.intrastat_unit_id and decl_line.suppl_unit_qty:
                etree.SubElement(measure, "SupplementaryUnitsQuantity").text = str(
                    decl_line.suppl_unit_qty
                )
                etree.SubElement(measure, "SupplementaryUnitsCode").text = (
                    decl_line.intrastat_unit_id.name or ""
                )

            # Nature of transaction (Swedish codes: 1, 2, 3...)
            nature = etree.SubElement(consignment, "NatureOfTransaction")
            etree.SubElement(nature, "Code").text = self._se_get_transaction_code(decl_line)

            # Transport mode
            if decl_line.transport_id:
                transport = etree.SubElement(consignment, "TransportMode")
                etree.SubElement(transport, "Code").text = (
                    decl_line.transport_id.code or "9"
                )

            # Delivery terms (incoterm)
            if decl_line.incoterm_id:
                delivery = etree.SubElement(consignment, "DeliveryTerms")
                etree.SubElement(delivery, "Code").text = decl_line.incoterm_id.code

            # Country of origin
            if decl_line.product_origin_country_code:
                origin = etree.SubElement(consignment, "CountryOfOrigin")
                etree.SubElement(origin, "Code").text = decl_line.product_origin_country_code

            # VAT number of partner (for dispatches)
            if self.declaration_type == "dispatches" and decl_line.vat:
                partner_vat = etree.SubElement(consignment, "Trader")
                etree.SubElement(partner_vat, "ID").text = decl_line.vat

        # Convert to bytes
        tree = etree.ElementTree(root)
        xml_bytes = BytesIO()
        tree.write(
            xml_bytes,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=True,
        )
        return xml_bytes.getvalue()

    def _se_get_declaration_type_code(self):
        """Get Swedish declaration type code."""
        return "INTRASTAT"

    def _se_get_functionary_code(self):
        """Get Swedish functionary code (always 'DECLARANT')."""
        return "DECLARANT"

    def _se_get_office_code(self):
        """Get Swedish customs office code for Intrastat (SCB)."""
        return "SCBINTRASTAT"

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
        """Map to Swedish transaction codes for SCB.
        Sweden uses numeric codes:
        1 = Outright purchase/sale
        2 = Return of goods
        3 = Free of charge delivery
        4 = Goods for processing/repair
        5 = Goods after processing/repair
        6 = Joint projects
        7 = Construction/engineering
        8 = Other
        """
        transaction = decl_line.transaction_id
        if not transaction:
            return "82"  # Default for Swedish Intrastat

        code = transaction.code or ""
        code_int = int(code) if code.isdigit() else 0

        # Map from OCA transaction codes to Swedish SCB codes
        se_mapping = {
            11: "11",  # Outright purchase/sale
            12: "11",  # Outright purchase/sale (B2C → B2B for Intrastat)
            21: "21",  # Return of goods
            22: "21",  # Return of goods (replacement)
            23: "21",  # Return of goods (other)
            31: "31",  # Free of charge
            41: "41",  # Processing/repair (sent)
            42: "52",  # Processing/repair (returned)
            51: "51",  # After processing (returned)
            52: "42",  # After processing (sent)
            61: "61",  # Joint projects
            71: "71",  # Construction/engineering
            81: "81",  # Other
            91: "82",  # Other (triangular trade for SE)
            99: "82",  # Other
        }
        return se_mapping.get(code_int, "82")
