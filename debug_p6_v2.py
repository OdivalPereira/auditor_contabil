import pdfplumber
import re
import os
from src.parsing.banks.sicoob import SicoobPDFParser

p = SicoobPDFParser()

# Let's find the file path reliably
base_path = r'extração_pdfs/pdf_modelos'
filename = 'Extrato Sicoob 10.2025.pdf'
f = os.path.join(base_path, filename)

if not os.path.exists(f):
    print(f"Error: File not found at {f}")
    # Try alternative if encoding is weird?
    # f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
    
pdf = pdfplumber.open(f)

# Debug Page 6 (index 5)
page = pdf.pages[5]
print(f"--- Debugging Page 6 (Index 5) ---")

txns, bs, be = p.extract_page(page)
print(f"\nExtracted Page 6: StartBal={bs}, EndBal={be}")
print(f"Transaction sum on Page 6: {sum(t['amount'] for t in txns):.2f}")
print(f"Transaction count on Page 6: {len(txns)}")

# Check coordinate of every token that looks like a number
words = page.extract_words()
print("\nCoordinate check for potential amounts in Sicoob (300 < x0 < 530):")
for w in words:
    txt = w['text']
    # Use the same regex as the parser
    if re.search(r'[\d\.,]+[CD\*]$', txt):
        val = p._parse_sicoob_amount(txt)
        print(f"  Token: {txt:<15} | Value: {val:>12.2f} | x0: {w['x0']:>7.2f} | top: {w['top']:>7.2f}")
