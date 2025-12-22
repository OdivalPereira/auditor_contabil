import pdfplumber
import re
from src.parsing.banks.sicoob import SicoobPDFParser

p = SicoobPDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
pdf = pdfplumber.open(f)

# Debug Page 6 (index 5)
page = pdf.pages[5]
print(f"--- Debugging Page 6 (Index 5) ---")
text = page.extract_text()
print("Raw Text Snippet (End):")
print(text[-500:])

txns, bs, be = p.extract_page(page)
print(f"\nExtracted Page 6: StartBal={bs}, EndBal={be}")
print(f"Transaction sum on Page 6: {sum(t['amount'] for t in txns):.2f}")
for t in txns:
    print(f"  {t['date']} | {t['amount']:>10.2f} | {t['description']}")

# Check coordinate of every token that looks like a number
words = page.extract_words()
print("\nCoordinate check for potential amounts:")
for w in words:
    txt = w['text']
    if re.search(r'[\d\.,]+[CD\*]$', txt):
        val = p._parse_sicoob_amount(txt)
        print(f"  Token: {txt:<15} | Value: {val:>10.2f} | x0: {w['x0']:>6.2f} | top: {w['top']:>6.2f}")
