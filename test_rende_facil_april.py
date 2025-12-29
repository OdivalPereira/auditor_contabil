"""
Test April 2025 extraction for Rende Fácil duplicates
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
from parsing.facade import ParserFacade

pdf_path = 'extratos/BB 04 2025.pdf'

print("=" * 80)
print("TESTING APRIL 2025 - RENDE FÁCIL")
print("=" * 80)

facade = ParserFacade()
df, metadata = facade.parse(pdf_path)

print(f"\nTotal transactions: {len(df)}")

# Filter for Rende Fácil on 25/04
rende_facil_25 = df[
    (pd.to_datetime(df['date']) == '2025-04-25') &
    (df['description'].str.contains('Rende F', case=False, na=False))
]

print(f"\n\nRende Fácil transactions on 25/04/2025:")
print(f"Count: {len(rende_facil_25)}")

if not rende_facil_25.empty:
    print("\nDetails:")
    for idx, row in rende_facil_25.iterrows():
        print(f"\n  Transaction {idx}:")
        print(f"    Date: {row['date']}")
        print(f"    Amount: {row['amount']}")
        print(f"    Description: {row['description']}")
        print(f"    Source: {row.get('source', 'N/A')}")
        if 'bal_row' in row:
            print(f"    Bal_row: {row['bal_row']}")

# Also check for any transaction with amount 693.24
print(f"\n\n{'='  * 80}")
print("Searching for transactions with amount 693.24:")
print("=" * 80)

txn_693 = df[abs(abs(df['amount']) - 693.24) < 0.01]
print(f"Found: {len(txn_693)}")

if not txn_693.empty:
    print("\nDetails:")
    for idx, row in txn_693.iterrows():
        print(f"\n  Transaction {idx}:")
        print(f"    Date: {row['date']}")
        print(f"    Amount: {row['amount']}")
        print(f"    Description: {row['description']}")
        print(f"    Source: {row.get('source', 'N/A')}")

# Check for any transaction with amount 49991.31
print(f"\n\n{'=' * 80}")
print("Searching for transactions with amount 49991.31:")
print("=" * 80)

txn_49991 = df[abs(abs(df['amount']) - 49991.31) < 0.01]
print(f"Found: {len(txn_49991)}")

if not txn_49991.empty:
    print("\nDetails:")
    for idx, row in txn_49991.iterrows():
        print(f"\n  Transaction {idx}:")
        print(f"    Date: {row['date']}")
        print(f"    Amount: {row['amount']}")
        print(f"    Description: {row['description']}")
        print(f"    Source: {row.get('source', 'N/A')}")

print(f"\n{'=' * 80}\n")
