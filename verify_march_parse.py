import sys
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser
import pandas as pd

parser = StonePDFParser()
pdf_path = 'extratos/Extrato Stones 03 2025.pdf'
df, meta = parser.parse(pdf_path)

print(f"Extracted {len(df)} transactions from {pdf_path}")
alex = df[df['description'].str.contains('Alex Rodrigues', case=False, na=False)]
if not alex.empty:
    print("\nALEX RODRIGUES ENTRIES:")
    print(alex[['date', 'description', 'amount']])
else:
    print("\nALEX RODRIGUES NOT FOUND IN FULL PARSE")

# Check values of 30.00 around late Feb / early Mar
print("\nTransactions of R$ 30.00 at start of March:")
print(df[(df['amount'] == 30.0) & (df['date'] < pd.Timestamp('2025-03-05').date())].head(10))
