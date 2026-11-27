# -*- coding: utf-8 -*-
# Copyright (C) 2026- Vertel Sverige AB
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""The Swedish VAT handler must reproduce the MIS amounts per box.

These tests build the taxes the extended chart ships (no tags, posting to
2610/2620/2630/2640) and assert the handler reports the same figures the
declaration used to get from MIS. That is the whole point of the handler:
those taxes are invisible to ``tax_tags``.
"""

from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestSeTaxReportHandler(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.country = cls.env.ref('base.se')
        cls.company.country_id = cls.country
        # Posting validates the tax against the company's FISCAL country, not
        # just its country_id. Without this every invoice is rejected with
        # "taxes incompatible with your fiscal country".
        cls.company.account_fiscal_country_id = cls.country
        cls.handler = cls.env['account.se.tax.report.handler']

        cls.report = cls.env['account.report'].create({
            'name': 'SE VAT Handler Test',
            'country_id': cls.country.id,
            'custom_handler_model_id':
                cls.env['ir.model']._get_id('account.se.tax.report.handler'),
            'column_ids': [(0, 0, {'name': 'Balance', 'expression_label': 'balance'})],
        })
        cls.line_10 = cls._line(cls, 'se_10', 'H_10', 10)
        cls.line_48 = cls._line(cls, 'se_48', 'H_48', 20)
        cls.line_05 = cls._line(cls, 'se_05', 'H_05', 30,
                                formula='_custom_expression_eval_base')

        cls.partner = cls.env['res.partner'].create({'name': 'SE VAT Test'})
        cls.sale_journal = cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.company.id)], limit=1)
        cls.purchase_journal = cls.env['account.journal'].search(
            [('type', '=', 'purchase'), ('company_id', '=', cls.company.id)], limit=1)

        # A sale tax shaped like the extended chart's MP1: no tags, 25 %.
        cls.tax_mp1 = cls._tax(cls, 'MP1', 'sale', 25.0)
        # A purchase tax shaped like I: no tags, 25 %.
        cls.tax_i = cls._tax(cls, 'I', 'purchase', 25.0)

    def _line(self, box, code, sequence, formula='_custom_expression_eval'):
        return self.env['account.report.line'].create({
            'name': 'Box %s' % box,
            'code': code,
            'report_id': self.report.id,
            'sequence': sequence,
            'expression_ids': [(0, 0, {
                'label': 'balance',
                'engine': 'custom',
                'formula': formula,
                'subformula': box,
            })],
        })

    def _tax(self, name, use, amount):
        tax = self.env['account.tax'].search([
            ('company_id', '=', self.company.id),
            ('name', '=', name),
            ('type_tax_use', '=', use),
        ], limit=1)
        if tax:
            return tax
        # account.tax.tax_group_id is NOT NULL; a bare create() fails.
        group = self.env['account.tax.group'].search(
            [('company_id', '=', self.company.id),
             ('country_id', '=', self.country.id)], limit=1)
        if not group:
            group = self.env['account.tax.group'].create({
                'name': 'Test group',
                'company_id': self.company.id,
                # The group's country must match the tax's, or validation fails.
                'country_id': self.country.id,
            })
        return self.env['account.tax'].create({
            'name': name,
            'amount': amount,
            'amount_type': 'percent',
            'type_tax_use': use,
            'company_id': self.company.id,
            'country_id': self.country.id,
            'tax_group_id': group.id,
            'invoice_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax'}),
            ],
            'refund_repartition_line_ids': [
                (0, 0, {'repartition_type': 'base'}),
                (0, 0, {'repartition_type': 'tax'}),
            ],
        })

    def _invoice(self, move_type, journal, amount, tax, date='2026-03-15'):
        move = self.env['account.move'].create({
            'move_type': move_type,
            'partner_id': self.partner.id,
            'journal_id': journal.id,
            'invoice_date': date,
            'date': date,
            'invoice_line_ids': [(0, 0, {
                'name': 'line',
                'quantity': 1,
                'price_unit': amount,
                'tax_ids': [(6, 0, tax.ids)],
            })],
        })
        move.action_post()
        return move

    def _options(self):
        return {
            'date': {'date_from': '2026-01-01', 'date_to': '2026-12-31'},
            'company_ids': [self.company.id],
            'unfold_all': True,
        }

    def _value(self, line):
        totals = self.report._compute_expression_totals(
            self.report.line_ids.expression_ids, self._options(),
        )
        return totals[(line.expression_ids.id, 'col_0')]

    def _baseline(self, line):
        """The report may already contain invoices from other tests or seed
        data, so every assertion is made on the delta this test adds.
        """
        return self._value(line)

    # ------------------------------------------------------------------
    def test_untagged_tax_is_seen(self):
        """The whole reason the handler exists: MP1 has no tags."""
        self.assertFalse(self.tax_mp1.invoice_repartition_line_ids.mapped('tag_ids'))
        base = self._baseline(self.line_10)
        self._invoice('out_invoice', self.sale_journal, 20000.0, self.tax_mp1)
        self.assertAlmostEqual(self._value(self.line_10) - base, 5000.0, 2)

    def test_incoming_vat_is_positive(self):
        """Box 48 reads positive for a vendor bill (balance is a debit)."""
        base = self._baseline(self.line_48)
        self._invoice('in_invoice', self.purchase_journal, 8000.0, self.tax_i)
        self.assertAlmostEqual(self._value(self.line_48) - base, 2000.0, 2)

    def test_credit_note_subtracts(self):
        """A credit note reduces the box -- MIS could not do this at all."""
        base = self._baseline(self.line_10)
        self._invoice('out_invoice', self.sale_journal, 20000.0, self.tax_mp1)
        self._invoice('out_refund', self.sale_journal, 4000.0, self.tax_mp1)
        # 5000 - 1000: the credit note subtracts, which MIS never managed.
        self.assertAlmostEqual(self._value(self.line_10) - base, 4000.0, 2)

    def test_box_05_is_the_base_amount(self):
        """Box 05 is the taxable base, not the tax."""
        base = self._baseline(self.line_05)
        self._invoice('out_invoice', self.sale_journal, 20000.0, self.tax_mp1)
        self.assertAlmostEqual(self._value(self.line_05) - base, 20000.0, 2)

    def test_draft_is_excluded(self):
        base = self._baseline(self.line_10)
        move = self._invoice('out_invoice', self.sale_journal, 20000.0, self.tax_mp1)
        move.button_draft()
        self.assertAlmostEqual(self._value(self.line_10) - base, 0.0, 2)

    def test_outside_period_is_excluded(self):
        base = self._baseline(self.line_10)
        self._invoice('out_invoice', self.sale_journal, 20000.0, self.tax_mp1,
                      date='2025-06-01')
        self.assertAlmostEqual(self._value(self.line_10) - base, 0.0, 2)

    def test_drilldown_sums_to_value(self):
        self._invoice('out_invoice', self.sale_journal, 20000.0, self.tax_mp1)
        value = self._value(self.line_10)
        signed = self.report._get_line_signed_amounts(self.line_10, self._options())
        self.assertAlmostEqual(sum(a for _l, a in signed), value, 2)

    def test_unknown_box_returns_zero(self):
        """A box with no tax mapping must render 0, not crash."""
        line = self._line('se_99', 'H_99', 99)
        self._invoice('out_invoice', self.sale_journal, 20000.0, self.tax_mp1)
        self.assertAlmostEqual(self._value(line), 0.0, 2)
