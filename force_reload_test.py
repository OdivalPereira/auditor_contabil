"""
FORCE RELOAD TEST - Testing new date-anchored Stone parser
"""
import sys
import importlib

# Clear ALL cached modules
modules_to_clear = [k for k in sys.modules.keys() if 'parsing' in k or 'stone' in k.lower()]
for mod in modules_to_clear:
    del sys.modules[mod]

# Now import fresh
from src.parsing.banks.stone import StonePDFParser

# Parse
parser = StonePDFParser()
df, meta = parser.parse('extratos/Extrato Stones 03 2025.pdf')

print("="*80)
print("FRESH IMPORT TEST")  
print("="*80)
print(f"Total transactions: {len(df)}")

pix_maq = df[df['description'].str.contains('Pix.*Maquininha', case=False, na=False, regex=True)]
print(f"Pix|Maquininha entries: {len(pix_maq)}")

# Check if they're all part of composite descriptions (correct) or standalone (wrong)
standalone = pix_maq[pix_maq['description'].str.strip() == 'Pix | Maquininha']
composite = pix_maq[pix_maq['description'].str.strip() != 'Pix | Maquininha']

print(f"  Standalone 'Pix | Maquininha': {len(standalone)} (BUG if > 0)")
print(f"  Composite descriptions: {len(composite)} (CORRECT)")

if len(standalone) > 0:
    print("\n❌ BUG: Still extracting standalone Pix|Maquininha as transactions!")
    print("Sample standalone:")
    print(standalone[['date', 'description', 'amount']].head(5))
else:
    print("\n✅ SUCCESS: All Pix|Maquininha are part of composite descriptions!")

print("="*80)
