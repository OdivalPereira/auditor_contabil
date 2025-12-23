import sys
import logging

logging.basicConfig(level=logging.ERROR)

# Clear modules
keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser
import pandas as pd

parser = StonePDFParser()
pdf_path = 'extratos/Extrato Stones 03 2025.pdf'

print("="*80)
print("DEBUGGING TARIFF FILTER")
print("="*80)

# Parse with our current logic
df, meta = parser.parse(pdf_path)

# Find all tariffs
tariffs = df[df['description'].str.contains('Débito Tarifa|debito tarifa', case=False, na=False, regex=True)]

print(f"\nTotal transactions extracted: {len(df)}")
print(f"Total tariffs in final result: {len(tariffs)}")

# Sample first 10 tariffs
print("\nFirst 10 tariffs in FINAL result (after filtering):")
print(tariffs[['date', 'description', 'amount']].head(10))

# Now let's manually check the raw extraction before filtering
print("\n" + "="*80)
print("MANUAL CHECK: What's happening in extract_page?")
print("="*80)

# Re-extract ONE page without filtering
import pdfplumber
pdf = pdfplumber.open(pdf_path)
page = pdf.pages[5]  # Pick a page with data

rows, _, _ = parser.extract_page(page)
raw_df = pd.DataFrame(rows)

print(f"\nRaw extraction from page 5: {len(raw_df)} rows")

if 'balance' in raw_df.columns:
    raw_tariffs = raw_df[raw_df['description'].str.contains('Débito Tarifa|debito tarifa', case=False, na=False, regex=True)]
    print(f"Raw tariffs from page 5: {len(raw_tariffs)}")
    
    print("\nChecking first 5 tariffs from raw extraction:")
    for i, row in raw_tariffs.head(5).iterrows():
        print(f"\nIndex {i}: {row['description'][:40]}...")
        print(f"  Balance: {row['balance']}")
        print(f"  Amount: {row['amount']}")
        
        # Check next row
        if i + 1 < len(raw_df):
            next_row = raw_df.iloc[i + 1]
            print(f"  Next row: {next_row['description'][:40]}...")
            print(f"  Next balance: {next_row['balance']}")
            print(f"  Balance diff: {abs(row['balance'] - next_row['balance'])}")
            
            if abs(row['balance'] - next_row['balance']) < 0.001:
                print(f"  -> SHOULD BE FILTERED (same balance)")
            else:
                print(f"  -> SHOULD BE KEPT (balance changed)")
else:
    print("ERROR: No balance column in raw data!")
