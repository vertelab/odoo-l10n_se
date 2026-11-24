# -*- coding: utf-8 -*-
# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import os

from lxml import etree

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestIntrastatXml(TransactionCase):
    """Verify that the generated file validates against instat62.xsd.

    SCB rejects anything that does not follow INSTAT/XML 6.2, and the element
    order in that schema is strict, so a passing test here is the minimum bar
    before a file is sent in.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write(
            {
                "intrastat_contact_name": "Test Testsson",
                "intrastat_contact_email": "test@vertel.se",
                "intrastat_contact_phone": "08-123456",
            }
        )
        cls.declaration = cls.env["intrastat.product.declaration"].create(
            {
                "company_id": cls.company.id,
                "declaration_type": "dispatches",
                "year": 2026,
                "month": "10",
                "reporting_level": "standard",
                "action": "replace",
                "revision": 1,
            }
        )
        cls.env["intrastat.product.declaration.line"].create(
            {
                "parent_id": cls.declaration.id,
                "line_number": 1,
                "amount_company_currency": 125000.0,
                "weight": 42.5,
                "src_dest_country_code": "DE",
                "transaction_id": cls.env.ref(
                    "intrastat_product.intrastat_transaction_11"
                ).id,
            }
        )

    def _schema(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "static",
            "spec",
            "instat62.xsd",
        )
        with open(path, "rb") as xsd:
            return etree.XMLSchema(etree.fromstring(xsd.read()))

    def test_xml_validates_against_instat62(self):
        xml = self.declaration._generate_xml()
        doc = etree.fromstring(xml)
        schema = self._schema()
        valid = schema.validate(doc)
        errors = "\n".join(
            f"line {e.line}: {e.message}" for e in schema.error_log
        )
        self.assertTrue(valid, f"XML does not validate against instat62.xsd:\n{errors}")

    def test_xml_root_and_flow(self):
        doc = etree.fromstring(self.declaration._generate_xml())
        self.assertEqual(doc.tag, "INSTAT")
        self.assertEqual(doc.findtext(".//flowCode"), "D")
        self.assertEqual(doc.findtext(".//referencePeriod"), "2026-10")
        self.assertEqual(doc.findtext(".//currencyCode"), "SEK")

    def test_xml_uses_eu_transaction_code(self):
        """The OCA codes ARE the EU codes SCB expects — no remapping."""
        doc = etree.fromstring(self.declaration._generate_xml())
        self.assertEqual(doc.findtext(".//natureOfTransactionACode"), "11")

    def test_arrivals_flow_code(self):
        self.declaration.write({"declaration_type": "arrivals"})
        doc = etree.fromstring(self.declaration._generate_xml())
        self.assertEqual(doc.findtext(".//flowCode"), "A")
