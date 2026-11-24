# -*- coding: utf-8 -*-
# Copyright 2026 Vertel Sverige AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import os
from unittest.mock import patch

from lxml import etree

from odoo.tests import tagged
from odoo.exceptions import UserError
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

    def test_software_used_matches_bilaga2_format(self):
        """SCB certifies the softwareUsed string — it must follow
        SW=softwarename;VER=softwareversion (Bilaga 2) and carry the running
        Odoo series, so 18.0/19.0/20.0 each produce their own string.
        """
        from odoo import release

        doc = etree.fromstring(self.declaration._generate_xml())
        value = doc.findtext(".//softwareUsed")
        self.assertEqual(value, f"SW=Odoo;VER={release.series}")
        self.assertRegex(value, r"^SW=[^;]+;VER=\d+\.\d+$")

    def test_arrivals_flow_code(self):
        self.declaration.write({"declaration_type": "arrivals"})
        doc = etree.fromstring(self.declaration._generate_xml())
        self.assertEqual(doc.findtext(".//flowCode"), "A")


@tagged("post_install", "-at_install")
class TestSwedishRules(TransactionCase):
    """Swedish reporting rules: monthly period and accessory costs."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.declaration = cls.env["intrastat.product.declaration"].create(
            {
                "company_id": cls.company.id,
                "declaration_type": "dispatches",
                "year": 2026,
                "month": "10",
                "reporting_level": "standard",
                "action": "replace",
            }
        )

    def test_period_requires_year(self):
        """year has no default and can be empty; the guard must catch it."""
        with patch.object(type(self.declaration), "year", False):
            with self.assertRaises(UserError):
                self.declaration._check_se_period()

    def test_period_rejects_invalid_month(self):
        """month is a selection, so an invalid value can only arrive through
        a bad import or a direct SQL write. _check_se_period must still guard.
        """
        self.declaration.month = "10"
        with patch.object(
            type(self.declaration), "month", "13"
        ):
            with self.assertRaises(UserError):
                self.declaration._check_se_period()

    def test_period_accepts_valid_month(self):
        for month in ("01", "06", "12"):
            self.declaration.month = month
            self.declaration._check_se_period()  # must not raise

    def test_accessory_costs_always_enabled(self):
        """The Swedish rule has no off position — gathering forces it on."""
        self.company.intrastat_accessory_costs = False
        self.declaration._gather_invoices(
            {"product": {}, "invoice": {}, "inv_origin": "", "invline_origin": ""}
        )
        self.assertTrue(
            self.company.intrastat_accessory_costs,
            "Accessory costs must be enabled for Swedish Intrastat",
        )

    def test_accessory_cost_distributed_pro_rata(self):
        lines = [
            {"amount_company_currency": 100.0, "weight": 10.0,
             "amount_accessory_cost_company_currency": 0.0},
            {"amount_company_currency": 300.0, "weight": 30.0,
             "amount_accessory_cost_company_currency": 0.0},
        ]
        self.declaration._handle_invoice_accessory_cost(
            self.env["account.move"], lines, 40.0, 400.0, 40.0
        )
        self.assertAlmostEqual(lines[0]["amount_accessory_cost_company_currency"], 10.0)
        self.assertAlmostEqual(lines[1]["amount_accessory_cost_company_currency"], 30.0)

    def test_accessory_cost_falls_back_to_weight(self):
        lines = [
            {"amount_company_currency": 0.0, "weight": 10.0,
             "amount_accessory_cost_company_currency": 0.0},
            {"amount_company_currency": 0.0, "weight": 30.0,
             "amount_accessory_cost_company_currency": 0.0},
        ]
        self.declaration._handle_invoice_accessory_cost(
            self.env["account.move"], lines, 40.0, 0.0, 40.0
        )
        self.assertAlmostEqual(lines[0]["amount_accessory_cost_company_currency"], 10.0)
        self.assertAlmostEqual(lines[1]["amount_accessory_cost_company_currency"], 30.0)

    def test_no_accessory_cost_is_noop(self):
        lines = [{"amount_company_currency": 100.0, "weight": 10.0,
                  "amount_accessory_cost_company_currency": 0.0}]
        self.declaration._handle_invoice_accessory_cost(
            self.env["account.move"], lines, 0.0, 100.0, 10.0
        )
        self.assertEqual(lines[0]["amount_accessory_cost_company_currency"], 0.0)
