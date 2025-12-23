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
print("VERIFYING FINAL STONE EXTRACTION")
print("="*80)

# Check for any remaining 'Tarifa'
tariffs = df[df['description'].str.contains('Tarifa', case=False, na=False)]
print(f"Total transactions: {len(df)}")
print(f"Tariffs remaining: {len(tariffs)}")

if len(tariffs) > 0:
    print("\nWARNING: Some tariffs remain:")
    for idx, row in tariffs.head(10).iterrows():
        print(f"  {row['description']}")

print("\n" + "="*80)
print("CHECKING BLOCK GROUPING EXAMPLES")
print("="*80)

# Look for specific names that were problematic
names = ['Eliane de Melo Pereira', 'Maikon Dias Leal', 'KEVIN HENRIQUE']
for name in names:
    matches = df[df['description'].str.contains(name, case=False, na=False)]
    print(f"\nMatches for '{name}': {len(matches)}")
    for idx, row in matches.iterrows():
        print(f"  {row['date']} | {row['description']}")

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
if len(tariffs) == 0:
    print("SUCCESS: All tariffs filtered out.")
else:
    print("FAILURE: Some tariffs still present.")
