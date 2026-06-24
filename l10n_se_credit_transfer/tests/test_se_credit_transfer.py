# Copyright 2026 Vertel AB (https://vertel.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import date

from lxml import etree

from odoo.tests import tagged, TransactionCase


def _setup_payment(cls, payment_method_ref, identifier, cpa_id=None, scheme=None):
    """Configure the payment method, mode, journal and partners for a test."""
    cls.payment_method = cls.env.ref(payment_method_ref)

    cls.env["account.payment.method.line"].create({
        "name": cls.payment_method.name,
        "payment_method_id": cls.payment_method.id,
        "journal_id": cls.journal.id,
    })

    mode_vals = {
        "name": "Swedish CT Mode",
        "payment_method_id": cls.payment_method.id,
        "company_id": cls.company.id,
        "bank_account_link": "fixed",
        "fixed_journal_id": cls.journal.id,
        "se_initiating_party_identifier": identifier,
    }
    if scheme:
        mode_vals["se_initiating_party_scheme"] = scheme
    if cpa_id:
        mode_vals["se_corporate_pay_agreement_id"] = cpa_id
    cls.payment_mode = cls.env["account.payment.mode"].create(mode_vals)


@tagged("post_install", "-at_install")
class TestSeCreditTransfer(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        cls.company = cls.env.ref("base.main_company")
        cls.company.write({
            "country_id": cls.env.ref("base.se").id,
            "vat": "SE123456789701",
            "se_initiating_party_identifier": "012345678ORI0001",
            "se_initiating_party_scheme": "BANK",
            "se_corporate_pay_agreement_id": False,
        })
        cls.company.partner_id.write({
            "city": "Stockholm",
            "zip": "111 22",
            "street": "Kungsgatan 1",
        })

        cls.bank = cls.env["res.bank"].create({
            "name": "SwedBank",
            "bic": "SWEDSESSXXX",
        })

        cls.company_bank = cls.env["res.partner.bank"].create({
            "partner_id": cls.company.partner_id.id,
            "acc_number": "SE7335536296831513338982",
            "acc_type": "iban",
            "bank_id": cls.bank.id,
        })
        cls.journal = cls.env["account.journal"].create({
            "name": "Swedish Bank Journal",
            "type": "bank",
            "code": "SEBK",
            "company_id": cls.company.id,
            "bank_account_id": cls.company_bank.id,
            "currency_id": cls.env.ref("base.SEK").id,
        })

        cls.partner = cls.env["res.partner"].create({
            "name": "Swedish Supplier AB",
            "country_id": cls.env.ref("base.se").id,
            "city": "Stockholm",
            "zip": "111 22",
            "street": "Kungsgatan 10",
        })

        cls.partner_bank = cls.env["res.partner.bank"].create({
            "partner_id": cls.partner.id,
            "acc_number": "SE4550000000058398257466",
            "acc_type": "iban",
            "bank_id": cls.bank.id,
        })

    def _create_payment_order(self):
        order = self.env["account.payment.order"].create({
            "payment_type": "outbound",
            "payment_mode_id": self.payment_mode.id,
            "company_partner_bank_id": self.company_bank.id,
            "company_id": self.company.id,
            "batch_booking": True,
            "charge_bearer": "SHAR",
        })

        self.env["account.payment.line"].create({
            "order_id": order.id,
            "partner_id": self.partner.id,
            "partner_bank_id": self.partner_bank.id,
            "currency_id": self.env.ref("base.SEK").id,
            "amount_currency": 5000.00,
            "date": date.today(),
            "communication": "Invoice 12345",
            "communication_type": "normal",
        })

        return order

    # -----------------------------------------------------------------
    # Generic (se_credit_transfer)
    # -----------------------------------------------------------------

    def test_01_generic_xml(self):
        _setup_payment(
            self, "l10n_se_credit_transfer.se_credit_transfer",
            "SIGNER12345", "CPA00000001",
        )
        order = self._create_payment_order()
        xml_bytes, filename = order.generate_se_payment_file()

        self.assertTrue(filename.startswith("sct_se_"))
        self.assertTrue(filename.endswith(".xml"))

        root = etree.fromstring(xml_bytes)
        ns = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}

        svc_lvl = root.xpath("//p:SvcLvl/p:Cd", namespaces=ns)
        self.assertEqual(svc_lvl[0].text, "NURG")

        self.assertFalse(root.xpath("//p:ChrgBr", namespaces=ns))
        self.assertFalse(root.xpath("//p:BtchBookg", namespaces=ns))
        self.assertFalse(root.xpath("//p:InitgPty/p:Nm", namespaces=ns))

        schme = root.xpath(
            "//p:GrpHdr/p:InitgPty/p:Id/p:OrgId/p:Othr/p:SchmeNm/p:Cd",
            namespaces=ns,
        )
        self.assertEqual(schme[0].text, "BANK")

        bic = root.xpath("//p:FinInstnId/p:BIC", namespaces=ns)
        self.assertTrue(bic)
        self.assertEqual(bic[0].text, "SWEDSESSXXX")

        amt = root.xpath("//p:InstdAmt", namespaces=ns)
        self.assertEqual(amt[0].get("Ccy"), "SEK")

        ibans = root.xpath("//p:IBAN", namespaces=ns)
        for iban in ibans:
            self.assertTrue(iban.text.startswith("SE"))

        dbtr_acct_ccy = root.xpath("//p:PmtInf/p:DbtrAcct/p:Ccy", namespaces=ns)
        self.assertEqual(dbtr_acct_ccy[0].text, "SEK")

        dbtr_id = root.xpath(
            "//p:PmtInf/p:Dbtr/p:Id/p:OrgId/p:Othr/p:Id", namespaces=ns)
        self.assertEqual(dbtr_id[0].text, "CPA00000001")
        dbtr_schme = root.xpath(
            "//p:PmtInf/p:Dbtr/p:Id/p:OrgId/p:Othr/p:SchmeNm/p:Cd",
            namespaces=ns,
        )
        self.assertEqual(dbtr_schme[0].text, "BANK")

    def test_02_missing_identifier_raises(self):
        _setup_payment(
            self, "l10n_se_credit_transfer.se_credit_transfer",
            "SIGNER12345", "CPA00000001",
        )
        order = self._create_payment_order()
        order.company_id.se_initiating_party_identifier = False
        order.payment_mode_id.se_initiating_party_identifier = False

        with self.assertRaises(Exception):
            order.generate_payment_file()

    def test_03_filename_format(self):
        _setup_payment(
            self, "l10n_se_credit_transfer.se_credit_transfer",
            "SIGNER12345", "CPA00000001",
        )
        order = self._create_payment_order()
        xml_bytes, filename = order.generate_se_payment_file()
        self.assertIn(order.name, filename)

    def test_04_non_swedbank_includes_btch_chrg(self):
        """Verify BtchBookg and ChrgBr are included for non-Swedbank banks."""
        nordea = self.env["res.bank"].create({
            "name": "Nordea",
            "bic": "NDEASESSXXX",
        })
        nordea_bank = self.env["res.partner.bank"].create({
            "partner_id": self.company.partner_id.id,
            "acc_number": "SE7335536296831513338982",
            "acc_type": "iban",
            "bank_id": nordea.id,
        })
        _setup_payment(
            self, "l10n_se_credit_transfer.se_credit_transfer",
            "SIGNER12345", "CPA00000001",
        )
        order = self.env["account.payment.order"].create({
            "payment_type": "outbound",
            "payment_mode_id": self.payment_mode.id,
            "company_partner_bank_id": nordea_bank.id,
            "company_id": self.company.id,
            "batch_booking": True,
            "charge_bearer": "SHAR",
        })
        self.env["account.payment.line"].create({
            "order_id": order.id,
            "partner_id": self.partner.id,
            "partner_bank_id": self.partner_bank.id,
            "currency_id": self.env.ref("base.SEK").id,
            "amount_currency": 5000.00,
            "date": date.today(),
            "communication": "Invoice 12345",
            "communication_type": "normal",
        })

        xml_bytes, filename = order.generate_se_payment_file()
        root = etree.fromstring(xml_bytes)
        ns = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}

        chrg = root.xpath("//p:ChrgBr", namespaces=ns)
        self.assertTrue(chrg)
        self.assertEqual(chrg[0].text, "SHAR")

        btch = root.xpath("//p:BtchBookg", namespaces=ns)
        self.assertTrue(btch)
        self.assertEqual(btch[0].text, "true")

    # -----------------------------------------------------------------
    # Swedbank MIG 2.0 (se_credit_transfer_20)
    # -----------------------------------------------------------------

    def test_20_swedbank_02_xml(self):
        _setup_payment(
            self, "l10n_se_credit_transfer.se_credit_transfer_20",
            "012345678ORI0001", "123456789CPO0001",
        )
        order = self._create_payment_order()
        xml_bytes, filename = order.generate_se_payment_file()

        self.assertTrue(filename.startswith("sct_se_"))

        root = etree.fromstring(xml_bytes)
        ns = {"p": "urn:iso:std:iso:20022:tech:xsd:pain.001.001.03"}

        svc_lvl = root.xpath("//p:SvcLvl/p:Cd", namespaces=ns)
        self.assertEqual(svc_lvl[0].text, "NURG")

        # 2.0 has no ChrgBr
        self.assertFalse(root.xpath("//p:ChrgBr", namespaces=ns))

        # 2.0 has no BtchBookg
        self.assertFalse(root.xpath("//p:BtchBookg", namespaces=ns))

        # 2.0 has InitgPty/Nm
        nm = root.xpath("//p:InitgPty/p:Nm", namespaces=ns)
        self.assertTrue(nm)

        # 2.0 uses BANK scheme
        schme = root.xpath(
            "//p:GrpHdr/p:InitgPty/p:Id/p:OrgId/p:Othr/p:SchmeNm/p:Cd",
            namespaces=ns,
        )
        self.assertEqual(schme[0].text, "BANK")

        # 2.0 has DbtrAgt/FinInstnId/PstlAdr/Ctry
        ctry = root.xpath(
            "//p:PmtInf/p:DbtrAgt/p:FinInstnId/p:PstlAdr/p:Ctry",
            namespaces=ns,
        )
        self.assertTrue(ctry)
        self.assertEqual(ctry[0].text, "SE")

        # 2.0 has Dbtr/Id with CPA ID
        dbtr_id = root.xpath(
            "//p:PmtInf/p:Dbtr/p:Id/p:OrgId/p:Othr/p:Id", namespaces=ns)
        self.assertEqual(dbtr_id[0].text, "123456789CPO0001")
        dbtr_schme = root.xpath(
            "//p:PmtInf/p:Dbtr/p:Id/p:OrgId/p:Othr/p:SchmeNm/p:Cd",
            namespaces=ns,
        )
        self.assertEqual(dbtr_schme[0].text, "BANK")
