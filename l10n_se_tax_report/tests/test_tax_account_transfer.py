from unittest.mock import patch

from odoo.tests import common, tagged


@tagged('-at_install', 'post_install')
class TestTaxAccountTransfer(common.TransactionCase):
    """The VAT debt must pass 2650 before it reaches 1630 (Skattekonto).

    Swedish standard (BAS):
        1. Period:      utgående moms 261x / ingående moms 264x
        2. Declaration: net against 2650 (Redovisningskonto för moms)
        3. Payment:     2650 <-> 1630 (Skattekonto)

    calculate() performs steps 2 and 3. The transfer to 1630 must be
    removed again when the declaration is reset to draft or cancelled.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.VatDeclaration = cls.env['account.vat.declaration']
        cls.AccountAccount = cls.env['account.account']
        cls.company = cls.env.company

        cls.journal = cls.env['account.journal'].search([
            ('company_id', '=', cls.company.id),
            ('name', '=', 'Momsjournal'),
            ('type', '=', 'general'),
            ('code', '=', 'MOMS'),
        ], limit=1)
        if not cls.journal:
            raise common.SkipTest('MOMS journal is not configured')

        cls.vat_debt = cls.journal.default_credit_account_id      # 2650
        cls.vat_receivable = cls.journal.default_debit_account_id  # 1650
        cls.tax_account = cls.AccountAccount.search([
            ('company_ids', 'in', [cls.company.id]),
            ('code', '=', '1630'),
        ], limit=1)
        if not (cls.vat_debt and cls.vat_receivable and cls.tax_account):
            raise common.SkipTest('2650/1650/1630 are not all configured')

    def _declaration(self, vat_amount):
        """A confirmed declaration whose vat_momsbetala is pinned.

        vat_momsbetala is a non-stored computed field, so it cannot be
        written. Patch the compute method instead, so the transfer logic
        can be exercised in isolation from the MIS report calculation.
        """
        declaration = self.VatDeclaration.create({
            'name': 'T10931 testdeklaration',
            'company_id': self.company.id,
            'date_start': '2099-01-01',
            'date_stop': '2099-01-31',
            'date': '2099-02-12',
            'state': 'confirmed',
        })

        def _fake_vat(records):
            for rec in records:
                rec.vat_momsbetala = vat_amount

        patcher = patch.object(
            type(declaration), '_vat', autospec=True, side_effect=_fake_vat)
        patcher.start()
        self.addCleanup(patcher.stop)
        declaration.invalidate_recordset()
        return declaration

    def _balance(self, account, declaration):
        return sum(declaration.skattekonto_move_id.line_ids.filtered(
            lambda line: line.account_id == account).mapped('balance'))

    def test_vat_debt_moves_to_tax_account(self):
        """VAT to pay: 2650 is debited, 1630 is credited.

        The debt is cleared on 2650 and re-booked as a debt to Skatteverket
        on 1630. The later payment debits 1630, which is how the historical
        manual entries are booked ("moms okt" credits 1630, "/bet moms"
        debits it).
        """
        declaration = self._declaration(10000)
        declaration._create_tax_account_transfer()

        self.assertTrue(declaration.skattekonto_move_id,
                        'A transfer entry must be created')
        # 2650 is a liability: debit -> positive balance (debt cleared)
        self.assertEqual(self._balance(self.vat_debt, declaration), 10000)
        # 1630 is a liability: credit -> negative balance (debt to SKV)
        self.assertEqual(self._balance(self.tax_account, declaration), -10000)

    def test_refund_moves_to_vat_receivable(self):
        """VAT refund: 1650 is credited, 1630 is debited."""
        declaration = self._declaration(-5000)
        declaration._create_tax_account_transfer()

        self.assertEqual(self._balance(self.vat_receivable, declaration), -5000)
        self.assertEqual(self._balance(self.tax_account, declaration), 5000)

    def test_transfer_is_idempotent(self):
        """Calling the transfer twice must not double-book."""
        declaration = self._declaration(10000)
        declaration._create_tax_account_transfer()
        first_move = declaration.skattekonto_move_id
        declaration._create_tax_account_transfer()

        self.assertEqual(declaration.skattekonto_move_id, first_move)
        self.assertEqual(self._balance(self.tax_account, declaration), -10000)

    def test_zero_vat_creates_no_transfer(self):
        """Nothing to pay and nothing to reclaim -> no entry."""
        declaration = self._declaration(0)
        declaration._create_tax_account_transfer()
        self.assertFalse(declaration.skattekonto_move_id)

    def test_do_draft_removes_the_transfer(self):
        """Resetting the declaration must not leave a balance on 1630."""
        declaration = self._declaration(10000)
        declaration._create_tax_account_transfer()
        self.assertTrue(declaration.skattekonto_move_id)

        declaration.do_draft()

        self.assertFalse(declaration.skattekonto_move_id,
                         'skattekonto_move_id must be cleared')
        remaining = self.env['account.move'].search([
            ('ref', '=', 'Momsdeklaration - överföring till skattekonto'),
            ('id', '=', declaration.id),
        ])
        self.assertFalse(remaining, 'The transfer entry must be deleted')

    def test_do_cancel_removes_the_transfer(self):
        declaration = self._declaration(10000)
        declaration._create_tax_account_transfer()
        declaration.do_cancel()
        self.assertFalse(declaration.skattekonto_move_id)

    def test_legacy_declaration_without_transfer_does_not_crash(self):
        """Declarations created before this feature have no transfer entry."""
        declaration = self._declaration(10000)
        self.assertFalse(declaration.skattekonto_move_id)
        declaration.do_draft()  # must not raise
        self.assertFalse(declaration.skattekonto_move_id)

    def test_transfer_is_posted(self):
        """The 2650 -> 1630 transfer must be posted, not left in draft.

        The reconciliation widget only considers posted move lines
        (account.bank.statement.line._get_default_amls_matching_domain sets
        parent_state = 'posted'). A draft transfer is therefore invisible in
        the bank reconciliation and the VAT debt cannot be matched.
        """
        declaration = self._declaration(10000)
        declaration._create_tax_account_transfer()
        move = declaration.skattekonto_move_id
        self.assertTrue(move, 'The transfer move was not created.')
        self.assertEqual(
            move.state, 'posted',
            'The transfer to the tax account must be posted, otherwise it is '
            'invisible to the bank reconciliation widget.',
        )

    def test_posted_transfer_shows_up_as_reconciliation_candidate(self):
        """The posted 1630 line is a valid counterpart candidate."""
        declaration = self._declaration(10000)
        declaration._create_tax_account_transfer()
        move = declaration.skattekonto_move_id
        tax_line = move.line_ids.filtered(
            lambda l: l.account_id.code == '1630')
        if not tax_line:
            self.skipTest('No 1630 line on the transfer.')

        journal = self.env['account.journal'].search(
            [('type', '=', 'bank')], limit=1)
        if not journal:
            self.skipTest('No bank journal available.')

        st_line = self.env['account.bank.statement.line'].new({
            'journal_id': journal.id,
            'amount': -(tax_line.debit - tax_line.credit),
            'payment_ref': 'Moms skattekonto',
        })
        domain = st_line._get_default_amls_matching_domain()
        candidates = self.env['account.move.line'].search(
            domain + [('id', '=', tax_line.id)])
        self.assertTrue(
            candidates,
            'The posted 1630 line must be offered as a reconciliation '
            'candidate.',
        )

