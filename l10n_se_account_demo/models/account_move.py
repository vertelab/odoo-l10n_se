"""Account Demo - loads demo journal entries on module install."""
import json
import logging
import os
from odoo import models, api

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _account_demo_load_moves(self):
        """Load 1273 demo journal entries from JSON.
        Resolves account references to l10n_se BAS accounts by code,
        tax references by amount+type. Idempotent."""
        data_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'account_demo_moves.json'
        )
        if not os.path.exists(data_path):
            _logger.warning('account_demo: JSON file not found at %s', data_path)
            return 0

        # Idempotency check
        self.env.cr.execute("""
            SELECT count(*) FROM account_move am
            JOIN account_move_line aml ON aml.move_id = am.id
            WHERE aml.display_type = 'payment_term'
              AND aml.date = '2025-01-27' AND aml.name = '21055'
        """)
        if self.env.cr.fetchone()[0] > 0:
            _logger.info('account_demo: moves already loaded, skipping')
            return 0

        _logger.info('account_demo: loading %d moves from JSON', 1273)
        with open(data_path, 'r') as f:
            all_moves = json.load(f)

        IrModelData = self.env['ir.model.data']

        def xmlid(ref_str):
            if not ref_str:
                return False
            return IrModelData._xmlid_to_res_id(ref_str) if ref_str else False

        # ── Account resolution: try XML ID, fall back to code lookup ──
        # Map known demo account codes → l10n_se account IDs
        demo_code_map = {
            '2610': ('2610', 'liability_non_current'),  # Utg moms 25%
            '2620': ('2620', 'liability_non_current'),  # Utg moms 12%
            '2640': ('2640', 'liability_non_current'),  # Ing moms
            '1510': ('1510', 'asset_receivable'),       # Kundfordringar
            '1930': ('1930', 'asset_cash'),             # Företagskonto
            '2440': ('2440', 'liability_payable'),      # Leverantörsskulder
            '3740': ('3740', 'income'),                 # Öresutjämning
            '8990': ('8990', 'equity'),                 # Resultat
            '3001': ('3001', 'income'),                 # Försäljning 25%
            '3002': ('3002', 'income'),                 # Försäljning 12%
            '4000': ('4000', 'expense_direct_cost'),    # Inköp varor
            '4001': ('4001', 'expense_direct_cost'),    # Inköp 25%
            '4002': ('4002', 'expense_direct_cost'),    # Inköp 12%
            '6540': ('6540', 'expense'),                # IT-tjänster
            '6550': ('6550', 'expense'),                # Konsultarvoden
            '6560': ('6560', 'expense'),                # Serviceavgifter
            '6570': ('6570', 'expense'),                # Bankkostnader
            '1229': ('1229', 'asset_fixed'),            # Avskr inventarier
            '1311': ('1311', 'asset_non_current'),      # Aktier koncern
            '1710': ('1710', 'asset_prepayments'),      # Förutb hyra
            '1730': ('1730', 'asset_prepayments'),      # Förutb försäkring
            '1940': ('1940', 'asset_cash'),             # Övr bankkonton
            '1950': ('1950', 'asset_cash'),             # Bankcertifikat
            '2126': ('2126', 'equity'),                 # Periodiseringsfond
            '2420': ('2420', 'asset_prepayments'),      # Förskott kunder
            '2821': ('2821', 'liability_non_current'),  # Löneskulder
            '4600': ('4600', 'expense_direct_cost'),    # Legoarbeten
            '5010': ('5010', 'expense'),                # Lokalhyra
            '5011': ('5011', 'expense'),                # Hyra kontor
            '5060': ('5060', 'expense'),                # Städning
            '5061': ('5061', 'expense'),                # Städning
            '5070': ('5070', 'expense'),                # Reparation
            '5160': ('5160', 'expense'),                # Städning
            '5410': ('5410', 'expense'),                # Förbrukningsinv
            '5420': ('5420', 'expense'),                # Programvaror
            '6000': ('6000', 'expense'),                # Försäljningskostn
            '6070': ('6070', 'expense'),                # Representation
            '6072': ('6072', 'expense'),                # Repr ej avdrag
            '6110': ('6110', 'expense'),                # Kontorsmateriel
            '6210': ('6210', 'expense'),                # Telekom
            '6212': ('6212', 'expense'),                # Mobiltelefon
            '6230': ('6230', 'expense'),                # Datakom
            '6250': ('6250', 'expense'),                # Postbefordran
            '6310': ('6310', 'expense'),                # Försäkringar
            '6970': ('6970', 'expense'),                # Tidningar
            '6990': ('6990', 'expense'),                # Övr externa
            '6991': ('6991', 'expense'),                # Övr externa avdr
            '6992': ('6992', 'expense'),                # Övr externa ej avdr
            '7410': ('7410', 'expense'),                # Pension
            '7411': ('7411', 'expense'),                # Pension kollektiv
            '7490': ('7490', 'expense'),                # Övr pension
            '7583': ('7583', 'expense'),                # Gruppförsäkring
            '7600': ('7600', 'expense'),                # Personalkostnader
            '7610': ('7610', 'expense'),                # Utbildning
            '7620': ('7620', 'expense'),                # Sjukvård
            '7631': ('7631', 'expense'),                # Personalrepr avdr
            '7632': ('7632', 'expense'),                # Personalrepr ej avdr
            '7690': ('7690', 'expense'),                # Övr personal
            '7699': ('7699', 'expense'),                # Övr personal
            '7832': ('7832', 'expense_direct_cost'),    # Avskrivningar
            '8400': ('8400', 'expense'),                # Räntekostnader
            '8420': ('8420', 'expense'),                # Ränta kortfrist
            '8422': ('8422', 'expense'),                # Dröjsmålsränta
            '8429': ('8429', 'expense'),                # Övr ränta kort
            # Non-standard codes → match by account_type fallback
            'K2513': ('1930', 'asset_cash'),             # Bank → 1930
            'K2519': ('1930', 'asset_cash'),             # Bankgiro → 1930
            'K2520': ('1930', 'asset_cash'),             # Bankgiro → 1930
            '1931': ('1939', 'asset_cash'),              # Bankobservationskonto
            '1932': ('1939', 'asset_cash'),              # Bank
            '4009': ('4009', 'expense_direct_cost'),     # Pant
        }

        # Type-based fallback lookup (lazy)
        _type_cache = {}
        def _account_by_type(account_type):
            if account_type in _type_cache:
                return _type_cache[account_type]
            account = self.env['account.account'].search([
                ('account_type', '=', account_type),
            ], limit=1)
            if account:
                _type_cache[account_type] = account.id
                return account.id
            return False

        # Map XML IDs to old account codes, then try code lookup → type fallback
        xmlid_to_code = {
            'l10n_se_account_demo.aa_1523': '2610', 'l10n_se_account_demo.aa_1531': '2620',
            'l10n_se_account_demo.aa_1547': '2640', 'l10n_se_account_demo.aa_1562': '1510',
            'l10n_se_account_demo.aa_1567': '1930', 'l10n_se_account_demo.aa_1568': '2440',
            'l10n_se_account_demo.aa_1570': '3740', 'l10n_se_account_demo.aa_1573': '8990',
            'l10n_se_account_demo.aa_1579': '3001', 'l10n_se_account_demo.aa_1580': '3002',
            'l10n_se_account_demo.aa_1582': '4000', 'l10n_se_account_demo.aa_1583': '4001',
            'l10n_se_account_demo.aa_1584': '4002', 'l10n_se_account_demo.aa_1604': '6540',
            'l10n_se_account_demo.aa_1607': '6550', 'l10n_se_account_demo.aa_1608': '6560',
            'l10n_se_account_demo.aa_1609': '6570', 'l10n_se_account_demo.aa_1661': '1229',
            'l10n_se_account_demo.aa_1691': '1311', 'l10n_se_account_demo.aa_1813': '1710',
            'l10n_se_account_demo.aa_1815': '1730', 'l10n_se_account_demo.aa_1833': '1940',
            'l10n_se_account_demo.aa_1834': '1950', 'l10n_se_account_demo.aa_1887': '2126',
            'l10n_se_account_demo.aa_1957': '2420', 'l10n_se_account_demo.aa_2008': '2821',
            'l10n_se_account_demo.aa_2161': '4600', 'l10n_se_account_demo.aa_2186': '5010',
            'l10n_se_account_demo.aa_2187': '5011', 'l10n_se_account_demo.aa_2194': '5060',
            'l10n_se_account_demo.aa_2195': '5061', 'l10n_se_account_demo.aa_2200': '5070',
            'l10n_se_account_demo.aa_2211': '5160', 'l10n_se_account_demo.aa_2246': '5410',
            'l10n_se_account_demo.aa_2249': '5420', 'l10n_se_account_demo.aa_2302': '6000',
            'l10n_se_account_demo.aa_2315': '6070', 'l10n_se_account_demo.aa_2317': '6072',
            'l10n_se_account_demo.aa_2321': '6110', 'l10n_se_account_demo.aa_2324': '6210',
            'l10n_se_account_demo.aa_2326': '6212', 'l10n_se_account_demo.aa_2330': '6230',
            'l10n_se_account_demo.aa_2331': '6250', 'l10n_se_account_demo.aa_2333': '6310',
            'l10n_se_account_demo.aa_2370': '6970', 'l10n_se_account_demo.aa_2374': '6990',
            'l10n_se_account_demo.aa_2375': '6991', 'l10n_se_account_demo.aa_2376': '6992',
            'l10n_se_account_demo.aa_2470': '7410', 'l10n_se_account_demo.aa_2471': '7411',
            'l10n_se_account_demo.aa_2484': '7490', 'l10n_se_account_demo.aa_2507': '7583',
            'l10n_se_account_demo.aa_2510': '7600', 'l10n_se_account_demo.aa_2511': '7610',
            'l10n_se_account_demo.aa_2512': '7620', 'l10n_se_account_demo.aa_2517': '7631',
            'l10n_se_account_demo.aa_2518': '7632', 'l10n_se_account_demo.aa_2523': '7690',
            'l10n_se_account_demo.aa_2527': '7699', 'l10n_se_account_demo.aa_2551': '7832',
            'l10n_se_account_demo.aa_2654': '8400', 'l10n_se_account_demo.aa_2663': '8420',
            'l10n_se_account_demo.aa_2665': '8422', 'l10n_se_account_demo.aa_2668': '8429',
            'l10n_se_account_demo.aa_2706': '1930',   # Banktillgodohavande → 1930
            'l10n_se_account_demo.aa_2715': '1930',   # Bank → 1930 (fallback)
            'l10n_se_account_demo.aa_2716': '1930',   # Bankobservationskonto → 1930 (fallback)
            'l10n_se_account_demo.aa_3728': '4009',   # Pant
            'l10n_se_account_demo.aa_3729': '1930',   # Bankgiro → 1930
            'l10n_se_account_demo.aa_3730': '1930',   # Bankgiro → 1930
        }

        def resolve_account(ref_str):
            if not ref_str: return False
            aid = xmlid(ref_str)
            if aid: return aid
            code = xmlid_to_code.get(ref_str)
            if not code: return False
            self.env.cr.execute(
                "SELECT id FROM account_account WHERE code_store->>'1' = %s",
                (code,))
            row = self.env.cr.fetchone()
            if row:
                return row[0]
            # Fallback: use any account with matching type from demo_code_map
            _logger.info('account_demo: account code %s not found, using type fallback', code)
            _, account_type = demo_code_map.get(code, (code, 'asset_cash'))
            return _account_by_type(account_type)

        # Tax resolution
        def resolve_tax(ref_str):
            if not ref_str: return False
            tid = xmlid(ref_str)
            if tid: return tid
            # Map demo tax name → l10n_se tax by amount+type
            tax_map = {
                'l10n_se_account_demo.tax_71': ('MP1', 25.0, 'sale'),
                'l10n_se_account_demo.tax_72': ('I', 25.0, 'purchase'),
                'l10n_se_account_demo.tax_74': ('MP2', 12.0, 'sale'),
                'l10n_se_account_demo.tax_115': ('IT', 25.0, 'purchase'),
                'l10n_se_account_demo.tax_116': ('Ii', 25.0, 'purchase'),
                'l10n_se_account_demo.tax_117': ('I12', 12.0, 'purchase'),
                'l10n_se_account_demo.tax_118': ('IT12', 12.0, 'purchase'),
            }
            if ref_str in tax_map:
                name, amount, ttype = tax_map[ref_str]
                tax = self.env['account.tax'].search([
                    ('name', 'ilike', name),
                    ('amount', '=', amount),
                    ('type_tax_use', '=', ttype),
                ], limit=1)
                if tax:
                    return tax.id
            return False

        def resolve_product(ref_str):
            if not ref_str: return False
            if '_template_' in ref_str:
                tmpl_id = xmlid(ref_str)
                if tmpl_id:
                    tmpl = self.env['product.template'].browse(tmpl_id)
                    return tmpl.product_variant_id.id if tmpl.product_variant_id else False
                return False
            return xmlid(ref_str) or False

        count = 0
        total = len(all_moves)
        for move_data in all_moves:
            vals = {
                'name': move_data.get('name'),
                'date': move_data.get('date'),
                'move_type': move_data.get('move_type'),
                'journal_id': xmlid(move_data.get('journal_id')),
                'company_id': xmlid(move_data.get('company_id', 'base.main_company')),
                'partner_id': xmlid(move_data.get('partner_id')),
                'currency_id': xmlid(move_data.get('currency_id', 'base.SEK')),
                'invoice_date': move_data.get('invoice_date'),
                'invoice_date_due': move_data.get('invoice_date_due'),
                'payment_reference': move_data.get('payment_reference'),
                'invoice_payment_term_id': xmlid(move_data.get('invoice_payment_term_id')),
                'fiscal_position_id': xmlid(move_data.get('fiscal_position_id')),
                'line_ids': [],
            }

            for line in move_data.get('line_ids', []):
                line_vals = {
                    'sequence': line.get('sequence'),
                    'date': line.get('date'),
                    'date_maturity': line.get('date_maturity'),
                    'account_id': resolve_account(line.get('account_id')),
                    'partner_id': xmlid(line.get('partner_id')),
                    'debit': line.get('debit', 0),
                    'credit': line.get('credit', 0),
                    'currency_id': xmlid(line.get('currency_id', 'base.SEK')),
                    'tax_line_id': resolve_tax(line.get('tax_line_id')),
                    'tax_group_id': xmlid(line.get('tax_group_id')),
                    'product_id': resolve_product(line.get('product_id')),
                    'display_type': line.get('display_type'),
                    'journal_id': xmlid(line.get('journal_id')),
                    'name': line.get('name'),
                }
                # Set price fields for product lines
                if line.get('display_type') == 'product':
                    amt = line.get('debit', 0) or line.get('credit', 0) or 0
                    line_vals['price_unit'] = float(amt)
                    line_vals['quantity'] = 1.0
                # Fallback: ensure date_maturity and display_type on receivable/payable
                if not line_vals.get('date_maturity'):
                    line_vals['date_maturity'] = (
                        move_data.get('invoice_date_due')
                        or move_data.get('date')
                    )
                # Odoo 18 requires payment_term display_type for receivable/payable lines
                acct_id = line_vals.get('account_id')
                if acct_id and not line.get('display_type'):
                    account = self.env['account.account'].browse(acct_id)
                    if account.account_type in ('asset_receivable', 'liability_payable'):
                        line_vals['display_type'] = 'payment_term'
                vals['line_ids'].append((0, 0, line_vals))

            move = self.with_context(check_move_validity=False).create(vals)

            # Set tax_ids on product lines from tax lines
            for ml in move.line_ids:
                if ml.display_type == 'product':
                    tax_ids = move.line_ids.filtered(
                        lambda l: l.display_type == 'tax' and l.tax_line_id
                    ).mapped('tax_line_id').ids
                    if tax_ids:
                        ml.write({'tax_ids': [(6, 0, tax_ids)]})

            count += 1
            if count % 100 == 0:
                self.env.cr.commit()
                _logger.info('account_demo: %d/%d moves loaded', count, total)

        _logger.info('account_demo: all %d moves loaded successfully', count)
        return count

    @api.model
    def _account_demo_load_bank_lines(self):
        """Create 4 bank statement lines in BNK1 for vendor bill reconciliation.
        Sets BNK1's suspense_account_id to 1519 (Avräkning) at runtime to avoid
        the default_account == suspense_account conflict (both 1930)."""
        data_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'account_demo_bank_lines.json'
        )
        if not os.path.exists(data_path):
            _logger.warning('account_demo: bank lines JSON not found at %s', data_path)
            return 0

        self.env.cr.execute("""
            SELECT count(*) FROM account_bank_statement_line
            WHERE payment_ref IN ('903096605626', '516187', '889131167', '74448889')
        """)
        if self.env.cr.fetchone()[0] > 0:
            _logger.info('account_demo: bank lines already loaded, skipping')
            return 0

        journal = self.env['account.journal'].search([('code', '=', 'BNK1')], limit=1)
        if not journal:
            _logger.warning('account_demo: BNK1 journal not found')
            return 0

        # Set suspense_account to 1519 (Avräkning) — avoids double-bank-line error
        self.env.cr.execute(
            "SELECT id FROM account_account WHERE code_store->>'1' = '1519'"
        )
        row = self.env.cr.fetchone()
        if not row:
            _logger.warning('account_demo: account 1519 not found for suspense')
            return 0
        suspense_account_id = row[0]
        if journal.suspense_account_id.id != suspense_account_id:
            journal.suspense_account_id = suspense_account_id

        SEK = self.env.ref('base.SEK')
        company = self.env.company

        with open(data_path, 'r') as f:
            lines_data = json.load(f)

        statement = self.env['account.bank.statement'].create({
            'journal_id': journal.id,
            'date': lines_data[0]['date'],
            'name': 'Demo bankhändelser för avstämning',
        })

        count = 0
        for line_data in lines_data:
            partner = self.env['res.partner'].search(
                [('vat', '=', line_data['partner_vat'])], limit=1
            ) if line_data.get('partner_vat') else False

            self.env['account.bank.statement.line'].create({
                'statement_id': statement.id,
                'journal_id': journal.id,
                'company_id': company.id,
                'amount': line_data['amount'],
                'partner_id': partner.id if partner else False,
                'partner_name': line_data['partner_name'],
                'payment_ref': line_data['payment_ref'],
                'currency_id': SEK.id,
            })
            count += 1

        _logger.info('account_demo: loaded %d bank statement lines', count)
        return count

    # Backward compatibility alias
    _account_demo_load_payments = _account_demo_load_bank_lines


def post_init_hook(env):
    """Post-install: load demo journal entries and bank lines via ORM."""
    move_count = env['account.move']._account_demo_load_moves()
    if move_count:
        env.cr.commit()
        _logger.info('account_demo: post_init_hook loaded %d journal entries', move_count)

    bank_count = env['account.move']._account_demo_load_bank_lines()
    if bank_count:
        env.cr.commit()
        _logger.info('account_demo: post_init_hook loaded %d bank statement lines', bank_count)
