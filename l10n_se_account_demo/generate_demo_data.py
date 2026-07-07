#!/usr/bin/env python3
"""
Generate account_demo XML data from scalinq-demo database.
All records use account_demo.* XML IDs for full portability.
No external dependencies except base.main_company, base.SEK, base.se.
"""
import psycopg2
import psycopg2.extras
import json
import sys
import os

DB_CONFIG = {
    'host': 'postgres16.vertel.se',
    'port': 5432,
    'user': 'scalinq',
    'password': '21mTMME/ZLCsEgnE29Klrg==',
    'database': 'scalinq-demo',
}

OUTPUT_FILE = '/usr/share/odoo-account/account_demo/data/account_demo.xml'
MOVES_JSON_FILE = '/usr/share/odoo-account/account_demo/data/account_demo_moves.json'
COMPANY_ID = 1

def connect():
    return psycopg2.connect(**DB_CONFIG)

def xml_escape(val):
    """Escape text for XML content (handles &, <, >)."""
    if val is None:
        return ''
    s = str(val)
    s = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return s

def fmt_date(val):
    if val is None:
        return ''
    return val.isoformat()

def main():
    conn = connect()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    print("Loading reference data...", file=sys.stderr)

    # --- 1. All accounts referenced in move lines ---
    cur.execute("""
        SELECT aa.* FROM account_account aa
        WHERE aa.id IN (
            SELECT DISTINCT account_id FROM account_move_line WHERE company_id = %s
        )
        ORDER BY aa.id
    """, (COMPANY_ID,))
    accounts = cur.fetchall()
    print(f"  Accounts: {len(accounts)}", file=sys.stderr)

    # Standard journal IDs that exist in all Odoo instances via account module
    STANDARD_JOURNALS = {15: 'account.1_sale', 16: 'account.1_purchase', 17: 'account.1_general'}

    # --- 2. All journals referenced in moves ---
    cur.execute("""
        SELECT aj.* FROM account_journal aj
        WHERE aj.id IN (
            SELECT DISTINCT journal_id FROM account_move WHERE company_id = %s
            UNION
            SELECT DISTINCT journal_id FROM account_move_line WHERE company_id = %s
        )
        ORDER BY aj.id
    """, (COMPANY_ID, COMPANY_ID))
    all_journals = cur.fetchall()
    # Only export custom journals (not the standard sale/purchase/general)
    journals = [j for j in all_journals if j['id'] not in STANDARD_JOURNALS]
    print(f"  Journals: {len(all_journals)} total, {len(journals)} custom to export", file=sys.stderr)

    # --- 3. All taxes used ---
    cur.execute("""
        SELECT DISTINCT at.* FROM account_tax at
        WHERE at.id IN (
            SELECT DISTINCT tax_line_id FROM account_move_line WHERE company_id = %s AND tax_line_id IS NOT NULL
        )
        ORDER BY at.id
    """, (COMPANY_ID,))
    taxes = cur.fetchall()
    print(f"  Taxes: {len(taxes)}", file=sys.stderr)

    # --- 4. Tax groups used ---
    cur.execute("""
        SELECT DISTINCT atg.* FROM account_tax_group atg
        WHERE atg.id IN (
            SELECT DISTINCT tax_group_id FROM account_move_line WHERE company_id = %s AND tax_group_id IS NOT NULL
        )
        ORDER BY atg.id
    """, (COMPANY_ID,))
    tax_groups = cur.fetchall()
    print(f"  Tax groups: {len(tax_groups)}", file=sys.stderr)

    # --- 5. Partners used ---
    cur.execute("""
        SELECT DISTINCT rp.* FROM res_partner rp
        WHERE rp.id IN (
            SELECT DISTINCT partner_id FROM account_move WHERE company_id = %s
            UNION
            SELECT DISTINCT partner_id FROM account_move_line WHERE company_id = %s
        )
        ORDER BY rp.id
    """, (COMPANY_ID, COMPANY_ID))
    partners = cur.fetchall()
    print(f"  Partners: {len(partners)}", file=sys.stderr)

    # --- 6. Fiscal positions used ---
    cur.execute("""
        SELECT DISTINCT afp.* FROM account_fiscal_position afp
        WHERE afp.id IN (
            SELECT DISTINCT fiscal_position_id FROM account_move WHERE company_id = %s AND fiscal_position_id IS NOT NULL
        )
    """, (COMPANY_ID,))
    fiscal_positions = cur.fetchall()
    print(f"  Fiscal positions: {len(fiscal_positions)}", file=sys.stderr)

    # --- 7. Payment terms used ---
    cur.execute("""
        SELECT DISTINCT apt.* FROM account_payment_term apt
        WHERE apt.id IN (
            SELECT DISTINCT invoice_payment_term_id FROM account_move WHERE company_id = %s AND invoice_payment_term_id IS NOT NULL
        )
    """, (COMPANY_ID,))
    payment_terms = cur.fetchall()
    print(f"  Payment terms: {len(payment_terms)}", file=sys.stderr)

    # --- 8. Products ---
    cur.execute("""
        SELECT DISTINCT pt.* FROM product_template pt
        WHERE pt.id IN (
            SELECT pt2.id FROM product_product pp
            JOIN product_template pt2 ON pt2.id = pp.product_tmpl_id
            WHERE pp.id IN (
                SELECT DISTINCT product_id FROM account_move_line WHERE company_id = %s AND product_id IS NOT NULL
            )
        )
    """, (COMPANY_ID,))
    products = cur.fetchall()
    print(f"  Products: {len(products)}", file=sys.stderr)

    cur.execute("""
        SELECT pp.* FROM product_product pp
        WHERE pp.id IN (
            SELECT DISTINCT product_id FROM account_move_line WHERE company_id = %s AND product_id IS NOT NULL
        )
    """, (COMPANY_ID,))
    product_variants = cur.fetchall()
    print(f"  Product variants: {len(product_variants)}", file=sys.stderr)

    # --- 9. Account moves ---
    cur.execute("""
        SELECT am.* FROM account_move am
        WHERE am.company_id = %s
        ORDER BY am.id
    """, (COMPANY_ID,))
    moves = cur.fetchall()
    print(f"  Account moves: {len(moves)}", file=sys.stderr)

    # --- 10. Account move lines ---
    cur.execute("""
        SELECT aml.* FROM account_move_line aml
        WHERE aml.company_id = %s
        ORDER BY aml.move_id, aml.id
    """, (COMPANY_ID,))
    move_lines = cur.fetchall()
    print(f"  Account move lines: {len(move_lines)}", file=sys.stderr)

    # --- 11. Currencies - SKIP, use existing base.SEK instead ---
    print(f"  Currencies: using base.SEK (existing)", file=sys.stderr)

    # Helper: XML ID for any referenced record
    def model_prefix(model):
        """Short prefix for model names used in XML IDs."""
        prefix_map = {
            'account.account': 'aa',
            'account.journal': 'journal',
            'account.tax': 'tax',
            'account.tax.group': 'tax_group',
            'res.partner': 'partner',
            'res.currency': 'currency',
            'account.fiscal.position': 'fiscal_pos',
            'account.payment.term': 'payment_term',
            'product.product': 'product',
            'product.template': 'product_template',
            'account.move': 'am',
        }
        return prefix_map.get(model, model.replace('.', '_'))

    def ref_id(model, id_val):
        """Return XML ID string for a record (used in JSON for resolving)."""
        if id_val is None:
            return None
        if model == 'res.currency':
            return 'base.SEK'
        if model == 'account.journal' and id_val in STANDARD_JOURNALS:
            return STANDARD_JOURNALS[id_val]
        return f'account_demo.{model_prefix(model)}_{id_val}'

    # --- Generate XML ---
    print(f"Generating XML to {OUTPUT_FILE}...", file=sys.stderr)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write('<odoo>\n')
        f.write('    <!--\n')
        f.write('    Account Demo Data - Scalinq AB\n')
        f.write(f'    Generated from scalinq-demo database\n')
        f.write(f'    {len(moves)} journal entries, {len(move_lines)} lines\n')
        f.write('    All records use account_demo.* XML IDs for portability\n')
        f.write('    -->\n\n')

        # Accounts
        if accounts:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Chart of Accounts                                            -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for acc in accounts:
                f.write(f'    <record id="aa_{acc["id"]}" model="account.account">\n')
                f.write(f'        <field name="name">{xml_escape(acc["name"])}</field>\n')
                if acc.get('code_store'):
                    f.write(f'        <field name="code_store">{xml_escape(json.dumps(acc["code_store"], ensure_ascii=False))}</field>\n')
                f.write(f'        <field name="account_type">{xml_escape(acc["account_type"])}</field>\n')
                f.write(f'        <field name="reconcile" eval="{acc["reconcile"]}"/>\n')
                if acc.get('deprecated'):
                    f.write(f'        <field name="deprecated" eval="True"/>\n')
                f.write(f'    </record>\n\n')

        # Journals
        if journals:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Journals                                                     -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for jn in journals:
                f.write(f'    <record id="journal_{jn["id"]}" model="account.journal">\n')
                f.write(f'        <field name="name">{xml_escape(jn["name"])}</field>\n')
                f.write(f'        <field name="type">{xml_escape(jn["type"])}</field>\n')
                if jn.get('code'):
                    f.write(f'        <field name="code">{xml_escape(jn["code"])}</field>\n')
                f.write(f'        <field name="company_id" ref="base.main_company"/>\n')
                f.write(f'    </record>\n\n')

        # Tax groups (before taxes since taxes reference groups)
        if tax_groups:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Tax Groups                                                   -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for tg in tax_groups:
                f.write(f'    <record id="tax_group_{tg["id"]}" model="account.tax.group">\n')
                f.write(f'        <field name="name">{xml_escape(tg["name"])}</field>\n')
                if tg.get('company_id'):
                    f.write(f'        <field name="company_id" ref="base.main_company"/>\n')
                if tg.get('country_id'):
                    f.write(f'        <field name="country_id" ref="base.se"/>\n')
                f.write(f'    </record>\n\n')

        # Taxes
        if taxes:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Taxes                                                        -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for tax in taxes:
                f.write(f'    <record id="tax_{tax["id"]}" model="account.tax">\n')
                f.write(f'        <field name="name">{xml_escape(tax["name"])}</field>\n')
                f.write(f'        <field name="amount" eval="{tax["amount"]}"/>\n')
                if tax.get('type_tax_use'):
                    f.write(f'        <field name="type_tax_use">{xml_escape(tax["type_tax_use"])}</field>\n')
                if tax.get('amount_type'):
                    f.write(f'        <field name="amount_type">{xml_escape(tax["amount_type"])}</field>\n')
                if tax.get('tax_group_id'):
                    f.write(f'        <field name="tax_group_id" ref="{ref_id("account.tax.group", tax["tax_group_id"])}"/>\n')
                if tax.get('company_id'):
                    f.write(f'        <field name="company_id" ref="base.main_company"/>\n')
                f.write(f'    </record>\n\n')

        # Partners
        if partners:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Partners                                                     -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for p in partners:
                f.write(f'    <record id="partner_{p["id"]}" model="res.partner">\n')
                f.write(f'        <field name="name">{xml_escape(p["name"])}</field>\n')
                if p.get('ref'):
                    f.write(f'        <field name="ref">{xml_escape(p["ref"])}</field>\n')
                if p.get('vat'):
                    f.write(f'        <field name="vat">{xml_escape(p["vat"])}</field>\n')
                if p.get('street'):
                    f.write(f'        <field name="street">{xml_escape(p["street"])}</field>\n')
                if p.get('city'):
                    f.write(f'        <field name="city">{xml_escape(p["city"])}</field>\n')
                if p.get('zip'):
                    f.write(f'        <field name="zip">{xml_escape(p["zip"])}</field>\n')
                if p.get('country_id'):
                    f.write(f'        <field name="country_id" ref="base.se"/>\n')
                if p.get('email'):
                    f.write(f'        <field name="email">{xml_escape(p["email"])}</field>\n')
                if p.get('phone'):
                    f.write(f'        <field name="phone">{xml_escape(p["phone"])}</field>\n')
                if p.get('is_company') is not None:
                    f.write(f'        <field name="is_company" eval="{p["is_company"]}"/>\n')
                if p.get('company_id'):
                    f.write(f'        <field name="company_id" ref="base.main_company"/>\n')
                f.write(f'    </record>\n\n')

        # Fiscal positions
        if fiscal_positions:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Fiscal Positions                                             -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for fp in fiscal_positions:
                f.write(f'    <record id="fiscal_pos_{fp["id"]}" model="account.fiscal.position">\n')
                f.write(f'        <field name="name">{xml_escape(fp["name"])}</field>\n')
                if fp.get('company_id'):
                    f.write(f'        <field name="company_id" ref="base.main_company"/>\n')
                f.write(f'    </record>\n\n')

        # Payment terms
        if payment_terms:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Payment Terms                                                -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for pt in payment_terms:
                f.write(f'    <record id="payment_term_{pt["id"]}" model="account.payment.term">\n')
                f.write(f'        <field name="name">{xml_escape(pt["name"])}</field>\n')
                if pt.get('company_id'):
                    f.write(f'        <field name="company_id" ref="base.main_company"/>\n')
                f.write(f'    </record>\n\n')

        # Products
        if products:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Product Templates                                            -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for prod in products:
                f.write(f'    <record id="product_template_{prod["id"]}" model="product.template">\n')
                f.write(f'        <field name="name">{xml_escape(prod["name"])}</field>\n')
                if prod.get('type'):
                    f.write(f'        <field name="type">{xml_escape(prod["type"])}</field>\n')
                if prod.get('list_price') is not None:
                    f.write(f'        <field name="list_price" eval="{prod["list_price"]}"/>\n')
                f.write(f'    </record>\n\n')

        if product_variants:
            f.write('    <!-- ============================================================ -->\n')
            f.write('    <!-- Product Variants                                             -->\n')
            f.write('    <!-- ============================================================ -->\n\n')
            for pv in product_variants:
                f.write(f'    <record id="product_{pv["id"]}" model="product.product">\n')
                f.write(f'        <field name="product_tmpl_id" ref="account_demo.product_template_{pv["product_tmpl_id"]}"/>\n')
                if pv.get('default_code'):
                    f.write(f'        <field name="default_code">{xml_escape(pv["default_code"])}</field>\n')
                f.write(f'    </record>\n\n')

        # Account Moves - written as JSON for post-init hook loading
        # (Odoo's create() for account.move does validation that fails on
        #  pre-balanced entries; JSON loading bypasses this with check_move_validity=False)
        if moves:
            print(f"  Writing {len(moves)} moves to JSON...", file=sys.stderr)
            lines_by_move = {}
            for line in move_lines:
                mid = line['move_id']
                if mid not in lines_by_move:
                    lines_by_move[mid] = []
                lines_by_move[mid].append(line)

            moves_json = []
            for move in moves:
                mid = move['id']
                m = {}
                if move.get('name'):
                    m['name'] = move['name']
                if move.get('ref'):
                    m['ref'] = move['ref']
                if move.get('date'):
                    m['date'] = fmt_date(move['date'])
                if move.get('move_type'):
                    m['move_type'] = move['move_type']
                if move.get('journal_id'):
                    m['journal_id'] = ref_id('account.journal', move['journal_id'])
                m['company_id'] = 'base.main_company'
                if move.get('partner_id'):
                    m['partner_id'] = ref_id('res.partner', move['partner_id'])
                if move.get('currency_id'):
                    m['currency_id'] = ref_id('res.currency', move['currency_id'])
                if move.get('invoice_date'):
                    m['invoice_date'] = fmt_date(move['invoice_date'])
                if move.get('invoice_date_due'):
                    m['invoice_date_due'] = fmt_date(move['invoice_date_due'])
                if move.get('invoice_payment_term_id'):
                    m['invoice_payment_term_id'] = ref_id('account.payment.term', move['invoice_payment_term_id'])
                if move.get('invoice_origin'):
                    m['invoice_origin'] = move['invoice_origin']
                if move.get('payment_reference'):
                    m['payment_reference'] = move['payment_reference']
                if move.get('narration'):
                    m['narration'] = move['narration']
                if move.get('fiscal_position_id'):
                    m['fiscal_position_id'] = ref_id('account.fiscal.position', move['fiscal_position_id'])

                move_lines_list = lines_by_move.get(mid, [])
                if move_lines_list:
                    ml_json = []
                    for line in move_lines_list:
                        l = {}
                        if line.get('name'):
                            l['name'] = line['name']
                        if line.get('ref'):
                            l['ref'] = line['ref']
                        if line.get('sequence') is not None:
                            l['sequence'] = line['sequence']
                        if line.get('date'):
                            l['date'] = fmt_date(line['date'])
                        if line.get('date_maturity'):
                            l['date_maturity'] = fmt_date(line['date_maturity'])
                        if line.get('account_id'):
                            l['account_id'] = ref_id('account.account', line['account_id'])
                        if line.get('partner_id'):
                            l['partner_id'] = ref_id('res.partner', line['partner_id'])
                        if line.get('debit') is not None:
                            l['debit'] = float(line['debit'])
                        if line.get('credit') is not None:
                            l['credit'] = float(line['credit'])
                        if line.get('currency_id'):
                            l['currency_id'] = ref_id('res.currency', line['currency_id'])
                        if line.get('tax_line_id'):
                            l['tax_line_id'] = ref_id('account.tax', line['tax_line_id'])
                        if line.get('tax_group_id'):
                            l['tax_group_id'] = ref_id('account.tax.group', line['tax_group_id'])
                        if line.get('product_id'):
                            l['product_id'] = ref_id('product.product', line['product_id'])
                        if line.get('display_type'):
                            l['display_type'] = line['display_type']
                        if line.get('journal_id'):
                            l['journal_id'] = ref_id('account.journal', line['journal_id'])
                        ml_json.append(l)
                    m['line_ids'] = ml_json

                moves_json.append(m)
                if mid % 100 == 0:
                    print(f"  Processed move {mid}...", file=sys.stderr)

            with open(MOVES_JSON_FILE, 'w', encoding='utf-8') as jf:
                json.dump(moves_json, jf, ensure_ascii=False, indent=2)

            json_size = os.path.getsize(MOVES_JSON_FILE)
            print(f"  Moves JSON: {MOVES_JSON_FILE} ({json_size:,} bytes)", file=sys.stderr)

        f.write('\n</odoo>\n')

    file_size = os.path.getsize(OUTPUT_FILE)
    print(f"Done! {OUTPUT_FILE} ({file_size:,} bytes)", file=sys.stderr)
    conn.close()

if __name__ == '__main__':
    main()
