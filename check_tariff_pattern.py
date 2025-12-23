import sys
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser

parser = StonePDFParser()
df, _ = parser.parse('extratos/Extrato Stones 03 2025.pdf')

print("="*80)
print("CHECKING TARIFF DESCRIPTIONS")
print("="*80)

# Find all entries with "Tarifa" in description
all_tarifa = df[df['description'].str.contains('Tarifa', case=False, na=False)]

print(f"\nTotal transactions: {len(df)}")
print(f"Entries with 'Tarifa': {len(all_tarifa)}")

print("\nFirst 20 'Tarifa' entries:")
for idx, row in all_tarifa.head(20).iterrows():
    print(f"{row['date']} | {row['description'][:60]:<60} | R$ {row['amount']:>8.2f}")

# Check specific patterns
debito_tarifa = df[df['description'].str.contains('Débito Tarifa|debito tarifa', case=False, na=False, regex=True)]
just_tarifa = df[df['description'].str.match(r'^Tarifa\s', case=False, na=False)]

print(f"\n'Débito Tarifa' pattern: {len(debito_tarifa)}")
print(f"'Tarifa NOME' pattern (starts with): {len(just_tarifa)}")

if len(just_tarifa) > 0:
    print("\nSample 'Tarifa NOME' entries:")
    for idx, row in just_tarifa.head(5).iterrows():
        print(f"  {row['description']}")
