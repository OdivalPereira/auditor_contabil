"""
Debug source field and transaction creation  
"""
import sys
sys.path.insert(0, 'src')

import pandas as pd
import pdfplumber
from parsing.banks.bb import BBMonthlyPDFParser

pdf_path = 'extratos/BB 04 2025.pdf'

print("="  * 80)
print("DETAILED PARSER DEBUG")
print("=" * 80)

# Test direct parser call (bypassing BaseParser)
parser = BBMonthlyPDFParser()

with pdfplumber.open(pdf_path) as pdf:
    all_rows = []
    bal_start_global = None
    bal_end_global = None
    
    for page_num, page in enumerate(pdf.pages, 1):
        rows, bal_start, bal_end = parser.extract_page(page)
        
        if bal_start is not None:
            bal_start_global = bal_start
        if bal_end is not None:
            bal_end_global = bal_end
        
        all_rows.extend(rows)
        
        # Check if this page has 25/04
        text = page.extract_text() or ""
        if "25/04/2025" in text and "Rende" in text:
            print(f"\nPage {page_num} contains Rende Fácil on 25/04")
            print(f"Rows extracted from this page: {len(rows)}")
            
            # Filter for 25/04
            april_25_rows = [r for r in rows if r.get('date') and r['date'].strftime('%Y-%m-%d') == '2025-04-25']
            print(f"25/04 transactions on this page: {len(april_25_rows)}")
            
            for i, row in enumerate(april_25_rows):
                print(f"\n  Row {i+1}:")
                print(f"    Amount: {row.get('amount')}")
                print(f"    Description: {row.get('description')}")
                print(f"    Source: {row.get('source')}")
                print(f"    bal_row: {row.get('bal_row')}")

# Create DF from all rows
df = pd.DataFrame(all_rows)

print(f"\n{'=' * 80}")
print("BEFORE SYNTHETIC INJECTION")
print("=" * 80)

rende_25_before = df[
    (pd.to_datetime(df['date']) == '2025-04-25') &
    (df['description'].str.contains('Rende', case=False, na=False))
]

print(f"\nRende Fácil on 25/04 (before synthetic): {len(rende_25_before)}")
for idx, row in rende_25_before.iterrows():
    print(f"\n  Transaction {idx}:")
    print(f"    Amount: {row['amount']}")
    print(f"    Description: {row['description']}")
    print(f"    Source: {row['source']}")

# Now apply synthetic injection
print(f"\n{'=' * 80}")
print("APPLYING SYNTHETIC INJECTION")
print("=" * 80)

df_with_synthetic = parser._inject_rende_facil_movements(df, bal_start_global, bal_end_global)

rende_25_after = df_with_synthetic[
    (pd.to_datetime(df_with_synthetic['date']) == '2025-04-25') &
    (df_with_synthetic['description'].str.contains('Rende', case=False, na=False))
]

print(f"\nRende Fácil on 25/04 (after synthetic): {len(rende_25_after)}")
for idx, row in rende_25_after.iterrows():
    print(f"\n  Transaction {idx}:")
    print(f"    Amount: {row['amount']}")
    print(f"    Description: {row['description']}")
    print(f"    Source: {row['source']}")

print(f"\n{'=' * 80}\n")
