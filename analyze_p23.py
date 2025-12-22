import pdfplumber
from src.parsing.banks.sicoob import SicoobPDFParser

p = SicoobPDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
pdf = pdfplumber.open(f)

page = pdf.pages[22]  # Page 23
txns, _, _ = p.extract_page(page)

print(f"Page 23 transactions: {len(txns)}")
print(f"Page 23 sum: {sum(t['amount'] for t in txns):.2f}")
print("\nTop 10 largest amounts:")
for t in sorted(txns, key=lambda x: -abs(x['amount']))[:10]:
    print(f"{t['amount']:>10.2f} | {t['description'][:60]}")
