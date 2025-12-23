import sys
if 'src.parsing.banks.stone' in sys.modules:
    del sys.modules['src.parsing.banks.stone']

from src.parsing.banks.stone import StonePDFParser
import pdfplumber
import re

# Test the parser
parser = StonePDFParser()
df, _ = parser.parse('extratos/Extrato Stones 03 2025.pdf')

print("="*80)
print("INVESTIGATING PIX | MAQUININHA EXTRACTION")
print("="*80)

# Find all Pix|Maquininha entries
pix_entries = df[df['description'].str.contains('Pix.*Maquininha', case=False, na=False, regex=True)]
print(f"\nTotal Pix|Maquininha entries: {len(pix_entries)}")

# Separate by amount sign
pix_positive = pix_entries[pix_entries['amount'] > 0]
pix_negative = pix_entries[pix_entries['amount'] < 0]
pix_with_names = pix_entries[~pix_entries['description'].str.match(r'^Pix \| Maquininha$', case=False, na=False)]

print(f"  Positive amounts: {len(pix_positive)}")
print(f"  Negative amounts: {len(pix_negative)}")  
print(f"  With customer names: {len(pix_with_names)}")

print("\nSample NEGATIVE Pix|Maquininha (should be continuation lines, NOT transactions):")
print(pix_negative[['date', 'description', 'amount']].head(10).to_string())

print("\nSample WITH names (correctly concatenated):")
print(pix_with_names[['date', 'description', 'amount']].head(5).to_string())

# Now check the PDF directly
print("\n" + "="*80)
print("CHECKING PDF RAW TEXT")
print("="*80)

pdf = pdfplumber.open('extratos/Extrato Stones 03 2025.pdf')
page = pdf.pages[-2]
text = page.extract_text()
lines = text.split('\n')

# Find lines with "Pix | Maquininha" that DON'T start with a date
date_pattern = re.compile(r'^\d{2}/\d{2}/\d{2}\s')
pix_lines_without_date = []
pix_lines_with_date = []

for i, line in enumerate(lines):
    if 'pix' in line.lower() and 'maqu' in line.lower():
        if date_pattern.match(line.strip()):
            pix_lines_with_date.append((i, line.strip()))
        else:
            pix_lines_without_date.append((i, line.strip()))

print(f"\nPDF lines with 'Pix | Maquininha':")
print(f"  WITHOUT date at start: {len(pix_lines_without_date)} (should be continuation lines)")
print(f"  WITH date at start: {len(pix_lines_with_date)} (valid transactions)")

print("\nFirst 5 WITHOUT date:")
for i, line in pix_lines_without_date[:5]:
    print(f"  Line {i}: [{line}]")

if pix_lines_with_date:
    print("\nFirst 5 WITH date:")
    for i, line in pix_lines_with_date[:5]:
        print(f"  Line {i}: [{line}]")

print("\n" + "="*80)
print("CONCLUSION:")
if len(pix_lines_without_date) > len(pix_negative):
    print(f"✓ Good: Parser is capturing {len(pix_negative)} but PDF has {len(pix_lines_without_date)} continuation lines")
    print(f"  Some are being correctly concatenated!")
elif len(pix_lines_without_date) == len(pix_negative):
    print(f"✗ BAD: All {len(pix_lines_without_date)} continuation lines are being extracted as transactions!")
else:
    print(f"? Parser extracted {len(pix_negative)} but PDF has {len(pix_lines_without_date)} continuation lines")
print("="*80)
