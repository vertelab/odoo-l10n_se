from odoo.tests import common, tagged
from odoo import fields
from odoo.exceptions import UserError
from datetime import date, timedelta

TEST_YEAR = 2099  # Far future year to avoid conflicts with existing data


@tagged('-at_install', 'post_install')
class TestPeriodicCompilation(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Product = cls.env['product.product']
        cls.Partner = cls.env['res.partner']
        cls.AccountMove = cls.env['account.move']
        cls.AccountTax = cls.env['account.tax']
        cls.AccountFiscalyear = cls.env['account.fiscal.year']
        cls.PeriodicCompilation = cls.env['account.periodic.compilation']
        cls.VatDeclaration = cls.env['account.vat.declaration']

        cls.tax_account = cls.env['account.account'].search([
            ('account_type', '=', 'asset_current'),
        ], limit=1)

        cls.income_account = cls.env['account.account'].search([
            ('account_type', '=', 'income'),
        ], limit=1)

        cls.eu_goods_account = cls.env['account.account'].search([
            ('code', '=', '3106'),
        ], limit=1)

        cls.receivable_account = cls.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
        ], limit=1)

        cls.expense_account = cls.env['account.account'].search([
            ('account_type', '=', 'expense'),
        ], limit=1)

        cls.sale_journal = cls.env['account.journal'].search([
            ('type', '=', 'sale'),
        ], limit=1)

        cls.general_journal = cls.env['account.journal'].search([
            ('type', '=', 'general'),
        ], limit=1)

        cls.purchase_journal = cls.env['account.journal'].search([
            ('type', '=', 'purchase'),
        ], limit=1)

        cls.eu_partner = cls.Partner.create({
            'name': 'EU Test Customer',
            'is_company': True,
            'country_id': cls.env.ref('base.de').id,
        })

        cls.eu_partner_2 = cls.Partner.create({
            'name': 'EU Test Customer 2',
            'is_company': True,
            'country_id': cls.env.ref('base.fr').id,
        })

        cls.non_eu_partner = cls.Partner.create({
            'name': 'Non-EU Customer',
            'is_company': True,
            'country_id': cls.env.ref('base.us').id,
        })

        cls.taxes = cls._get_or_create_taxes(cls)

        cls.fiscalyear = cls.AccountFiscalyear.create({
            'name': 'Test Fiscal Year %d' % TEST_YEAR,
            'date_from': date(TEST_YEAR, 1, 1),
            'date_to': date(TEST_YEAR, 12, 31),
            'company_id': cls.env.company.id,
        })

    def _get_or_create_taxes(self):
        Tax = self.env['account.tax']
        result = {}

        tax_defs = [
            ('vteu', 'VTEU', 'sale', 0.0, 'Försäljning varor till annat EU-land'),
            ('fteu', 'FTEU', 'sale', 0.0, 'Försäljning tjänster till annat EU-land'),
            ('e_tax', 'E', 'sale', 0.0, 'Försäljning utanför EU'),
            ('vfeu', 'VFEU', 'purchase', 25.0, 'Inköp varor från annat EU-land'),
            ('3feu', '3FEU', 'purchase', 0.0, 'Mellanmans försäljning trepartshandel'),
        ]

        for key, name, tax_type, amount, desc in tax_defs:
            tax = Tax.search([('name', '=', name)], limit=1)
            if not tax:
                tax_type_map = {'sale': 'sale', 'purchase': 'purchase'}
                tax = Tax.create({
                    'name': name,
                    'amount': amount,
                    'amount_type': 'percent',
                    'type_tax_use': tax_type_map[tax_type],
                    'description': desc,
                    'price_include': False,
                    'invoice_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                            'factor_percent': 100,
                        }),
                        (0, 0, {
                            'repartition_type': 'tax',
                            'factor_percent': 100,
                            'account_id': self.tax_account.id,
                        }),
                    ],
                    'refund_repartition_line_ids': [
                        (0, 0, {
                            'repartition_type': 'base',
                            'factor_percent': 100,
                        }),
                        (0, 0, {
                            'repartition_type': 'tax',
                            'factor_percent': 100,
                            'account_id': self.tax_account.id,
                        }),
                    ],
                })
            result[key] = tax
        return result

    def _create_product(self, name, tax):
        return self.Product.create({
            'name': name,
            'type': 'service',
            'taxes_id': [(6, 0, tax.ids)] if tax else False,
        })

    def _create_invoice(self, partner, move_type, product, qty, price, journal=None, account=None):
        account = account or (self.income_account if move_type in ('out_invoice', 'out_refund') else self.expense_account)
        invoice = self.AccountMove.create({
            'move_type': move_type,
            'partner_id': partner.id,
            'journal_id': (journal or self.sale_journal).id,
            'invoice_date': date(TEST_YEAR, 6, 15),
            'invoice_line_ids': [
                (0, 0, {
                    'product_id': product.id,
                    'quantity': qty,
                    'price_unit': price,
                    'name': product.name,
                    'account_id': account.id,
                    'tax_ids': [(6, 0, product.taxes_id.ids)],
                }),
            ],
        })
        invoice.action_post()
        return invoice

    def test_create_periodic(self):
        pc = self.PeriodicCompilation.create({
            'name': 'Test PC',
            'date_start': date(TEST_YEAR, 1, 1),
            'date_stop': date(TEST_YEAR, 1, 31),
        })
        self.assertEqual(pc.state, 'draft')
        self.assertEqual(pc.name, 'Test PC')

    def test_calculate_with_eu_goods(self):
        """VTEU on generic income account (not 3106) — caught via invoice iteration."""
        prod = self._create_product('EU Goods', self.taxes['vteu'])
        self._create_invoice(
            self.eu_partner, 'out_invoice', prod, 10, 1000,
            account=self.income_account,
        )
        self._create_invoice(
            self.eu_partner, 'out_invoice', prod, 5, 2000,
            account=self.income_account,
        )

        pc = self.PeriodicCompilation.create({
            'name': 'EU Goods Test',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(pc.state, 'confirmed')
        self.assertEqual(len(pc.line_ids), 1)
        self.assertEqual(
            pc.line_ids.pc_supplied_goods, 20000.0,
            "VTEU goods should be 10*1000 + 5*2000 = 20000")

    def test_calculate_with_eu_services(self):
        prod = self._create_product('EU Service', self.taxes['fteu'])
        self._create_invoice(self.eu_partner, 'out_invoice', prod, 3, 1500)

        pc = self.PeriodicCompilation.create({
            'name': 'EU Service Test',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(len(pc.line_ids), 1)
        self.assertEqual(
            pc.line_ids.pc_services_supplied, 4500.0,
            "FTEU services should be 3*1500 = 4500")

    def test_calculate_group_by_partner(self):
        """VTEU goods on generic income account, FTEU services on another account."""
        prod_vteu = self._create_product('EU Goods', self.taxes['vteu'])
        prod_fteu = self._create_product('EU Service', self.taxes['fteu'])

        self._create_invoice(
            self.eu_partner, 'out_invoice', prod_vteu, 10, 1000,
            account=self.income_account,
        )
        self._create_invoice(
            self.eu_partner, 'out_invoice', prod_fteu, 2, 500,
        )
        self._create_invoice(
            self.eu_partner_2, 'out_invoice', prod_vteu, 5, 3000,
            account=self.income_account,
        )

        pc = self.PeriodicCompilation.create({
            'name': 'Group By Partner',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(len(pc.line_ids), 2)
        line_1 = pc.line_ids.filtered(lambda l: l.partner_id == self.eu_partner)
        line_2 = pc.line_ids.filtered(lambda l: l.partner_id == self.eu_partner_2)
        self.assertEqual(len(line_1), 1)
        self.assertEqual(len(line_2), 1)
        self.assertEqual(line_1.pc_supplied_goods, 10000.0)
        self.assertEqual(line_1.pc_services_supplied, 1000.0)
        self.assertEqual(line_2.pc_supplied_goods, 15000.0)

    def test_calculate_non_eu_not_included(self):
        prod_e = self._create_product('Export', self.taxes['e_tax'])
        self._create_invoice(self.non_eu_partner, 'out_invoice', prod_e, 10, 1000)

        pc = self.PeriodicCompilation.create({
            'name': 'Non-EU excluded',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(len(pc.line_ids), 0, "E-tax should not match VTEU/FTEU/3FEU")

    def test_do_draft_reset(self):
        """VTEU on generic income account, should work after do_draft too."""
        prod = self._create_product('EU Goods', self.taxes['vteu'])
        self._create_invoice(
            self.eu_partner, 'out_invoice', prod, 10, 1000,
            account=self.income_account,
        )

        pc = self.PeriodicCompilation.create({
            'name': 'Draft Reset',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(len(pc.line_ids), 1)
        pc.do_draft()
        self.assertEqual(pc.state, 'draft')
        self.assertEqual(len(pc.line_ids), 0,
                         "Lines should be cleared after do_draft")

    def test_manual_entry_on_3106_without_tax_warns(self):
        """A manual entry crediting 3106 without a tax code must be refused
        at posting time.

        Box 35 of the periodic compilation is defined by the VTEU/VTEU3 tax
        codes, not by the account. A line on 3106 with no tax at all is
        therefore undefined for the report and would silently drop out of the
        declaration. The guard lives in account.move._post() so the mistake is
        caught where it is made.
        """
        if not self.eu_goods_account or not self.general_journal:
            self.skipTest("Missing account 3106 or general journal")

        manual_move = self.AccountMove.create({
            'move_type': 'entry',
            'partner_id': self.eu_partner.id,
            'journal_id': self.general_journal.id,
            'date': date(TEST_YEAR, 6, 20),
            'line_ids': [
                (0, 0, {
                    'name': 'EU goods via manual entry, no tax',
                    'account_id': self.receivable_account.id,
                    'debit': 15000.0,
                    'credit': 0.0,
                    'partner_id': self.eu_partner.id,
                }),
                (0, 0, {
                    'name': 'EU goods via manual entry, no tax',
                    'account_id': self.eu_goods_account.id,
                    'debit': 0.0,
                    'credit': 15000.0,
                    'partner_id': self.eu_partner.id,
                }),
            ],
        })
        with self.assertRaises(UserError):
            manual_move.action_post()

    def test_manual_entry_on_3106_with_vteu_is_caught(self):
        """A manual entry on 3106 carrying VTEU must reach box 35, and must be
        summed with invoice-based VTEU goods on the same account."""
        if not self.eu_goods_account or not self.general_journal:
            self.skipTest("Missing account 3106 or general journal")

        vteu = self.taxes['vteu']

        # Invoice-based VTEU goods on 3106
        prod = self._create_product('EU Goods', vteu)
        self._create_invoice(
            self.eu_partner, 'out_invoice', prod, 10, 1000,
            account=self.eu_goods_account,
        )

        # Manual entry on 3106, WITH VTEU
        manual_move = self.AccountMove.create({
            'move_type': 'entry',
            'partner_id': self.eu_partner.id,
            'journal_id': self.general_journal.id,
            'date': date(TEST_YEAR, 6, 20),
            'line_ids': [
                (0, 0, {
                    'name': 'Manual EU goods with VTEU',
                    'account_id': self.receivable_account.id,
                    'debit': 5000.0,
                    'credit': 0.0,
                    'partner_id': self.eu_partner.id,
                }),
                (0, 0, {
                    'name': 'Manual EU goods with VTEU',
                    'account_id': self.eu_goods_account.id,
                    'debit': 0.0,
                    'credit': 5000.0,
                    'partner_id': self.eu_partner.id,
                    'tax_ids': [(6, 0, vteu.ids)],
                }),
            ],
        })
        manual_move.action_post()

        pc = self.PeriodicCompilation.create({
            'name': 'Manual Entry With VTEU',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(pc.state, 'confirmed')
        line = pc.line_ids.filtered(lambda l: l.partner_id == self.eu_partner)
        self.assertEqual(len(line), 1)
        # 10 * 1000 (invoice) + 5000 (manual) = 15000
        self.assertEqual(
            line.pc_supplied_goods, 15000.0,
            "Invoice-based and manual VTEU entries on 3106 should be summed")

    def test_manual_entry_on_3106_without_tax_allowed_when_disabled(self):
        """The guard is per company and can be switched off, so a company that
        deliberately posts corrections on 3106 without a tax code is not
        blocked."""
        if not self.eu_goods_account or not self.general_journal:
            self.skipTest("Missing account 3106 or general journal")

        self.env.company.pc_warn_supplied_goods_without_tax = False

        manual_move = self.AccountMove.create({
            'move_type': 'entry',
            'partner_id': self.eu_partner.id,
            'journal_id': self.general_journal.id,
            'date': date(TEST_YEAR, 6, 20),
            'line_ids': [
                (0, 0, {
                    'name': 'Correction on 3106, no tax',
                    'account_id': self.receivable_account.id,
                    'debit': 1000.0,
                    'credit': 0.0,
                    'partner_id': self.eu_partner.id,
                }),
                (0, 0, {
                    'name': 'Correction on 3106, no tax',
                    'account_id': self.eu_goods_account.id,
                    'debit': 0.0,
                    'credit': 1000.0,
                    'partner_id': self.eu_partner.id,
                }),
            ],
        })
        # Must not raise
        manual_move.action_post()
        self.assertEqual(manual_move.state, 'posted')

    def test_mis_kpi_consistency_with_vat(self):
        """Periodic compilation should agree with the VAT report's Ruta 35
        (ForsVaruAnnatEg) for EU goods, since both use the same MIS report
        engine."""
        if not self.eu_goods_account or not self.general_journal:
            self.skipTest("Missing account 3106 or general journal")

        date_start = date(TEST_YEAR, 6, 1)
        date_stop = date(TEST_YEAR, 6, 30)

        # Create entries on 3106 that both reports should catch
        prod = self._create_product('EU Goods', self.taxes['vteu'])
        self._create_invoice(
            self.eu_partner, 'out_invoice', prod, 10, 1000,
            account=self.eu_goods_account,
        )
        self._create_invoice(
            self.eu_partner_2, 'out_invoice', prod, 5, 2000,
            account=self.eu_goods_account,
        )

        # Manual entry on 3106
        manual_move = self.AccountMove.create({
            'move_type': 'entry',
            'partner_id': self.eu_partner.id,
            'journal_id': self.general_journal.id,
            'date': date(TEST_YEAR, 6, 20),
            'line_ids': [
                (0, 0, {
                    'name': 'Manual EU goods',
                    'account_id': self.receivable_account.id,
                    'debit': 3000.0,
                    'credit': 0.0,
                    'partner_id': self.eu_partner.id,
                }),
                (0, 0, {
                    'name': 'Manual EU goods',
                    'account_id': self.eu_goods_account.id,
                    'debit': 0.0,
                    'credit': 3000.0,
                    'partner_id': self.eu_partner.id,
                    'tax_ids': [(6, 0, self.taxes['vteu'].ids)],
                }),
            ],
        })
        manual_move.action_post()

        # Create PC
        pc = self.PeriodicCompilation.create({
            'name': 'Consistency Test',
            'date_start': date_start,
            'date_stop': date_stop,
        })
        pc.calculate()

        # Create VAT declaration for same period
        vat_decl = self.VatDeclaration.create({
            'name': 'VAT Cons Test',
            'date_start': date_start,
            'date_stop': date_stop,
        })

        # Get the VAT report's box 35 value.
        amounts = vat_decl._get_box_amounts()
        vat_goods_value = abs(amounts.get('se_35', 0.0))

        # PC total goods should match VAT box 35
        pc_goods_total = sum(pc.line_ids.mapped('pc_supplied_goods'))
        self.assertAlmostEqual(
            pc_goods_total, vat_goods_value, delta=1.0,
            msg="PC total goods should match VAT box 35")

    def test_report_created(self):
        """The periodic compilation points at an account.report.

        Before the migration it auto-created a MIS Builder instance. That
        instance is gone; the compilation now references the report it is
        computed from, and the period comes from the compilation's own dates.
        """
        pc = self.PeriodicCompilation.create({
            'name': 'Report Test',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        self.assertTrue(
            pc.generated_report_id,
            "The compilation should reference an account.report")
        self.assertEqual(pc.generated_report_id._name, 'account.report')
        self.assertFalse(
            pc.generated_mis_report_id,
            "No MIS instance should be created any more")

    def test_same_data_via_invoice_and_report(self):
        """When EU goods are on account 3106 with VTEU tax, they should
        appear only ONCE in the PC (not double-counted via both the report
        drill-down and the invoice iteration)."""
        if not self.eu_goods_account:
            self.skipTest("Missing account 3106")

        prod = self._create_product('EU Goods', self.taxes['vteu'])
        self._create_invoice(
            self.eu_partner, 'out_invoice', prod, 10, 1000,
            account=self.eu_goods_account,
        )

        pc = self.PeriodicCompilation.create({
            'name': 'No Double Count',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(len(pc.line_ids), 1)
        self.assertEqual(
            pc.line_ids.pc_supplied_goods, 10000.0,
            "Should not double-count: 10*1000 = 10000, not 20000")

    def test_pc_name_shows_buyer_company_for_invoice_address(self):
        """T/12519 — the buyer name must not be empty for an invoice address.

        An invoice address (``type='invoice'``) carries no ``name`` of its own:
        Odoo composes "Company, Invoice Address" in ``complete_name``. Reading
        the raw ``partner_id.name`` therefore printed a VAT number with no
        buyer name. ``pc_name`` must resolve through the commercial entity.
        """
        company = self.Partner.create({
            'name': 'DANSK VVS Import A/S',
            'is_company': True,
            'country_id': self.env.ref('base.dk').id,
            'vat': 'DK73184517',
        })
        invoice_address = self.Partner.create({
            'parent_id': company.id,
            'type': 'invoice',
            'country_id': self.env.ref('base.dk').id,
        })
        # The premise of the bug: the address itself has no name, but does
        # inherit the VAT number.
        self.assertFalse(invoice_address.name)
        self.assertEqual(invoice_address.vat, 'DK73184517')

        prod = self._create_product('EU Goods', self.taxes['vteu'])
        self._create_invoice(
            invoice_address, 'out_invoice', prod, 10, 1000,
            account=self.income_account,
        )

        pc = self.PeriodicCompilation.create({
            'name': 'Invoice Address Name',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(len(pc.line_ids), 1)
        line = pc.line_ids
        self.assertEqual(
            line.pc_name, 'DANSK VVS Import A/S',
            "pc_name must fall back to the commercial entity when the "
            "invoice address has no name of its own")
        self.assertEqual(
            line.pc_purchasers_vat, 'DK73184517',
            "the VAT number must still be shown")
