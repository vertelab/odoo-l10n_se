#!/usr/bin/env python3
import pandas as pd
import sys
from pathlib import Path


def parse_kommun_bas(excel_path, output_csv_path, prefix="a"):
    """
    Parse Excel file and generate CSV for Odoo

    Args:
        excel_path: Path to the Excel file
        output_csv_path: Path for the output CSV file
        prefix: Prefix for XML IDs (default: a, we should consider using l10n_se_kommun )
    """
    # Read Excel file
    df = pd.read_excel(excel_path, sheet_name=0)

    # The header is in row 1 (0-indexed), data starts from row 2
    df.columns = df.iloc[1]
    df = df[2:].reset_index(drop=True)

    # Clean column names - remove the "1" prefix that appears
    df.columns = [str(col).split(' ', 1)[-1] if isinstance(col, str) and ' ' in col else col for col in df.columns]

    # Map to internal names
    column_map = {
        'Konto-klass': 'konto_klass',
        'Konto-grupp': 'konto_grupp',
        'Konto': 'konto',
        'Under-konto': 'under_konto',
        'Namn': 'namn',
        'Kontotext': 'kontotext'
    }
    df.rename(columns=column_map, inplace=True)

    # Filter rows that have a valid 'konto' or 'under_konto' value
    df_filtered = df[(df['konto'].notna()) | (df['under_konto'].notna())].copy()

    # Create the CSV records
    csv_records = []

    for idx, row in df_filtered.iterrows():
        # Determine the account code
        if pd.notna(row['under_konto']):
            code = str(int(row['under_konto']))
        elif pd.notna(row['konto']):
            code = str(int(row['konto']))
        else:
            continue

        # Generate the XML ID
        xml_id = f"{prefix}{code}" # {prefix}_{code}

        # Get the name (trim whitespace)
        name = str(row['namn']).strip() if pd.notna(row['namn']) else ""

        # Get the note/description and clean it for CSV
        note = ""
        if pd.notna(row['kontotext']):
            note = str(row['kontotext'])
            # Replace newlines with spaces
            note = note.replace('\n', ' ').replace('\r', ' ')
            # Replace multiple spaces with single space
            note = ' '.join(note.split())
            # Trim to reasonable length if needed
            note = note[:1000] if len(note) > 1000 else note

        # Create CSV record
        record = {
            'id': xml_id,
            'code': code,
            'name': name,
            'account_type': 'liability_non_current', # maybe have a function to determine this later account_type _determine_account_type(row)
            'reconcile': False,
            'note': note,
            'name@sv_SE': name,
            'tax_ids': ''
        }

        csv_records.append(record)

    # Create DataFrame and save to CSV
    df_output = pd.DataFrame(csv_records)

    # Ensure output directory exists
    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Save with proper quoting to handle commas and special characters
    df_output.to_csv(output_csv_path, index=False, quoting=2)

    print(f"✓ Parsed {len(csv_records)} accounts")
    print(f"✓ Output saved to: {output_csv_path}")

    return len(csv_records)

def _determine_account_type(self, row):
        """
        Determine the Odoo account_type based on the konto_klass

        Odoo account types:
        - asset_receivable
        - asset_cash
        - asset_current
        - asset_non_current
        - asset_prepayments
        - asset_fixed
        - liability_payable
        - liability_credit_card
        - liability_current
        - liability_non_current
        - equity
        - equity_unaffected
        - income
        - income_other
        - expense
        - expense_depreciation
        - expense_direct_cost
        - off_balance
        """
        klass = row['konto_klass']

        if pd.isna(klass):
            return 'liability_non_current'

        klass = int(klass)

        # to be continued


def _should_reconcile(self, row):
    """Determine if account should have reconcile enabled"""
    # Enable reconcile for receivables and payables
    account_type = self._determine_account_type(row)
    return account_type in ['asset_receivable', 'liability_payable']

def main():
    if len(sys.argv) < 2:
        print("Usage: python kommun_bas_parser.py <input_excel_file> [output_csv_file]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "kommun_bas_accounts.csv"
    prefix = "a" # we should consider l10n_se_kommun for uniqueness.

    # Convert to Path objects for better path handling
    input_path = Path(input_file)

    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)

    try:
        count = parse_kommun_bas(str(input_path), output_file, prefix)
        print(f"\n✓ Successfully processed {count} accounts")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()