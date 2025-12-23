"""
Simple check: Are tariffs really being filtered?
"""
import sys
import os

# Suppress all warnings/logging
os.environ['PYTHONWARNINGS'] = 'ignore'

# Clear modules  
keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser

parser = StonePDFParser()
df, _ = parser.parse('extratos/Extrato Stones 03 2025.pdf')

# Count tariffs
tariffs = df[df['description'].str.contains('Débito Tarifa|debito tarifa', case=False, na=False, regex=True)]

print(f"Total transactions: {len(df)}")
print(f"Total tariffs: {len(tariffs)}")
print(f"Percentage tariffs: {100*len(tariffs)/len(df):.1f}%")

# Show a few examples
print("\n" + "="*80)
print("Sample tariffs that were KEPT:")
print("="*80)
for idx, row in tariffs.head(10).iterrows():
    print(f"{row['date']} | {row['description'][:50]:<50} | R$ {row['amount']:>8.2f}")

print("\n" + "="*80)    
print("CONCLUSION: If we're seeing ~1900 tariffs, the filter ISN'T working.")
print("Expected: <100 tariffs (only those that truly change balance)")
print("="*80)
