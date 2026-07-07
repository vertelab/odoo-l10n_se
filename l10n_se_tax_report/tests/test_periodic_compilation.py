from odoo.tests import common, tagged
from odoo import fields
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
        cls.AccountFiscalyear = cls.env['account.fiscalyear']
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
            'code': str(TEST_YEAR),
            'date_start': date(TEST_YEAR, 1, 1),
            'date_stop': date(TEST_YEAR, 12, 31),
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
            'fiscalyear_id': self.fiscalyear.id,
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
            'fiscalyear_id': self.fiscalyear.id,
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
            'fiscalyear_id': self.fiscalyear.id,
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
            'fiscalyear_id': self.fiscalyear.id,
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
            'fiscalyear_id': self.fiscalyear.id,
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
            'fiscalyear_id': self.fiscalyear.id,
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(len(pc.line_ids), 1)
        pc.do_draft()
        self.assertEqual(pc.state, 'draft')
        self.assertEqual(len(pc.line_ids), 0,
                         "Lines should be cleared after do_draft")

    def test_manual_entry_on_3106_caught_by_mis(self):
        """Manual journal entry on account 3106 should be caught by MIS
        drilldown, even though there is no invoice line with VTEU tax.
        This is the core fix for the reported bug."""
        if not self.eu_goods_account or not self.general_journal:
            self.skipTest("Missing account 3106 or general journal")

        # Create a manual journal entry: debit 1510, credit 3106
        manual_move = self.AccountMove.create({
            'move_type': 'entry',
            'partner_id': self.eu_partner.id,
            'journal_id': self.general_journal.id,
            'date': date(TEST_YEAR, 6, 20),
            'line_ids': [
                (0, 0, {
                    'name': 'EU goods via manual entry',
                    'account_id': self.receivable_account.id,
                    'debit': 15000.0,
                    'credit': 0.0,
                    'partner_id': self.eu_partner.id,
                }),
                (0, 0, {
                    'name': 'EU goods via manual entry',
                    'account_id': self.eu_goods_account.id,
                    'debit': 0.0,
                    'credit': 15000.0,
                    'partner_id': self.eu_partner.id,
                }),
            ],
        })
        manual_move.action_post()

        pc = self.PeriodicCompilation.create({
            'name': 'Manual Entry Test',
            'fiscalyear_id': self.fiscalyear.id,
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        pc.calculate()
        self.assertEqual(pc.state, 'confirmed')
        self.assertGreater(
            len(pc.line_ids), 0,
            "Periodic compilation should have lines for the manual entry")
        line = pc.line_ids.filtered(lambda l: l.partner_id == self.eu_partner)
        self.assertEqual(len(line), 1)
        self.assertGreater(
            line.pc_supplied_goods, 0,
            "Manual entry on 3106 should be included in pc_supplied_goods")

    def test_mis_catches_both_invoice_and_manual(self):
        """Periodic compilation should include both invoice-based VTEU
        goods and manual entries on account 3106, giving the same total
        as the VAT report's Ruta 35 (ForsVaruAnnatEg)."""
        if not self.eu_goods_account or not self.general_journal:
            self.skipTest("Missing account 3106 or general journal")

        # Invoice-based VTEU goods on 3106
        income_account_3106 = self.eu_goods_account
        prod = self._create_product('EU Goods', self.taxes['vteu'])
        self._create_invoice(
            self.eu_partner, 'out_invoice', prod, 10, 1000,
            account=income_account_3106,
        )

        # Manual entry on 3106 (no VTEU tax)
        manual_move = self.AccountMove.create({
            'move_type': 'entry',
            'partner_id': self.eu_partner.id,
            'journal_id': self.general_journal.id,
            'date': date(TEST_YEAR, 6, 20),
            'line_ids': [
                (0, 0, {
                    'name': 'Manual EU goods',
                    'account_id': self.receivable_account.id,
                    'debit': 5000.0,
                    'credit': 0.0,
                    'partner_id': self.eu_partner.id,
                }),
                (0, 0, {
                    'name': 'Manual EU goods',
                    'account_id': self.eu_goods_account.id,
                    'debit': 0.0,
                    'credit': 5000.0,
                    'partner_id': self.eu_partner.id,
                }),
            ],
        })
        manual_move.action_post()

        pc = self.PeriodicCompilation.create({
            'name': 'Combined Test',
            'fiscalyear_id': self.fiscalyear.id,
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
            "Both invoice-based and manual entries on 3106 should be summed")

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

        # Get VAT report KPI value for ForsVaruAnnatEg
        if vat_decl.generated_mis_report_id:
            matrix = vat_decl.generated_mis_report_id._compute_matrix()
            vat_goods_value = 0.0
            for row in matrix.iter_rows():
                if row.kpi.name == 'ForsVaruAnnatEg':
                    vals = [c.val for c in row.iter_cells()]
                    if isinstance(vals[0], (float, int)):
                        vat_goods_value = abs(vals[0])

            # PC total goods should match VAT Ruta 35
            pc_goods_total = sum(pc.line_ids.mapped('pc_supplied_goods'))
            self.assertAlmostEqual(
                pc_goods_total, vat_goods_value, delta=1.0,
                msg="PC total goods should match VAT Ruta 35 (ForsVaruAnnatEg)")

    def test_mis_instance_created(self):
        """A MIS report instance should be automatically created when
        the periodic compilation is created."""
        pc = self.PeriodicCompilation.create({
            'name': 'MIS Instance Test',
            'date_start': date(TEST_YEAR, 6, 1),
            'date_stop': date(TEST_YEAR, 6, 30),
        })
        self.assertTrue(
            pc.generated_mis_report_id,
            "A MIS report instance should be auto-created")
        self.assertEqual(
            pc.generated_mis_report_id.period_ids[0].manual_date_from,
            date(TEST_YEAR, 6, 1),
        )
        self.assertEqual(
            pc.generated_mis_report_id.period_ids[0].manual_date_to,
            date(TEST_YEAR, 6, 30),
        )

    def test_same_data_via_invoice_and_mis(self):
        """When EU goods are on account 3106 with VTEU tax, they should
        appear only ONCE in the PC (not double-counted via both MIS
        drilldown and invoice iteration)."""
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
