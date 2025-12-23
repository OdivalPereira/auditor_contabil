import sys
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser

parser = StonePDFParser()
df, _ = parser.parse('extratos/Extrato Stones 02 2025.pdf')

print("="*80)
print("VERIFYING FIX FOR ABSURD VALUES (CPF/CNPJ)")
print("="*80)

# Check for the specific problematic entries found in the report
problematic_nums = ['44.142.170', '25.068.106', '1.498.299', '93.272.090', '44560265100']

count_absurd = 0
for idx, row in df.iterrows():
    val = abs(row['amount'])
    if val > 1000000: # Values in the millions/billions are definitely noise in this context
        print(f"ABSURD VALUE DETECTED: {row['date']} | {row['description']} | R$ {row['amount']:,.2f}")
        count_absurd += 1

print(f"\nTotal absurd values found: {count_absurd}")

# Check specific example
print("\nChecking specific entry 'NEY DA SILVA BORGES':")
ney_matches = df[df['description'].str.contains('NEY DA SILVA BORGES', case=False, na=False)]
for idx, row in ney_matches.iterrows():
    print(f"  {row['date']} | {row['description']} | R$ {row['amount']:,.2f} | Balance: {row.get('balance', 'N/A')}")

print("\n" + "="*80)
if count_absurd == 0:
    print("SUCCESS: No absurd values found.")
else:
    print("FAILURE: Absurd values still present.")
