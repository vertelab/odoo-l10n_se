from odoo import fields
from odoo.tests import tagged

from .test_counterpart import TestBankStatementCounterpart


@tagged("post_install", "-at_install")
class TestReconcileEpd(TestBankStatementCounterpart):

    def test_widget_reconcile_after_epd_booking(self):
        """Reproduce the reconciliation widget on a line with EPD lines.

        The widget deletes every non-liquidity line and rebuilds them from
        the reconcile data. If the EPD lines are deleted but the payable is
        not restored to its original amount, the entry becomes unbalanced.
        """
        partner = self.env["res.partner"].create({"name": "EPD Widget Vendor"})
        term = self._make_discount_term()
        bill = self._make_discounted_bill("BILL/EPD/0001", partner, term)

        term_line = bill.line_ids.filtered("discount_date")
        discounted_amount = term_line.discount_balance

        st_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.journal.id,
                "payment_ref": bill.name,
                "partner_id": partner.id,
                "amount": discounted_amount,
                "date": fields.Date.today(),
            }
        )
        move = st_line.move_id

        print("\n=== EFTER IMPORT ===")
        for ml in move.line_ids.sorted(lambda l: l.id):
            print(f"  {ml.account_id.code:>6} D{ml.debit:>8.2f} K{ml.credit:>8.2f} bal={ml.balance:>8.2f} type={ml.display_type}")
        print(f"  SUM D={sum(move.line_ids.mapped('debit')):.2f} K={sum(move.line_ids.mapped('credit')):.2f}")

        liq, susp, other = st_line._seek_for_lines()
        print(f"  liquidity={liq.mapped(lambda l: l.account_id.code)}")
        print(f"  suspense={susp.mapped(lambda l: l.account_id.code)}")
        print(f"  other={other.mapped(lambda l: l.account_id.code)}")
        print(f"  KOMMER RADERAS: {(susp | other).mapped(lambda l: l.account_id.code)}")
        print(f"  kvar efter delete: {liq.mapped(lambda l: (l.account_id.code, l.balance))}")
        print(f"  SALDO EFTER DELETE = {sum(liq.mapped('balance')):.2f}")

        # Widgetens clean_reconcile
        st_line.clean_reconcile()
        data = st_line.reconcile_data_info["data"]
        print("\n=== WIDGETENS DATA ===")
        for d in data:
            print(f"  kind={d['kind']:<10} acct={d.get('account_id')} "
                  f"D={d.get('debit',0):.2f} K={d.get('credit',0):.2f} "
                  f"cp={d.get('counterpart_line_ids')}")

        # Själva avstämningen
        print("\n=== RECONCILE ===")
        try:
            st_line.reconcile_bank_line()
            print("  OK")
        except Exception as e:
            print(f"  FEL: {type(e).__name__}: {e}")
            raise

        print(f"  bill payment_state={bill.payment_state} residual={bill.amount_residual}")
