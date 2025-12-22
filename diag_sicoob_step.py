import pdfplumber
from src.parsing.banks.sicoob import SicoobPDFParser

p = SicoobPDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
pdf = pdfplumber.open(f)

current_bal = 20883.58
print(f"Start: {current_bal}")

for i, page in enumerate(pdf.pages):
    txns, bs, be = p.extract_page(page)
    page_sum = sum(t['amount'] for t in txns)
    current_bal += page_sum
    
    # Try to find SALDO DO DIA on this page
    text = page.extract_text()
    import re
    m = re.search(r"SALDO DO DIA\s+([\d\.,]+)([CD])", text)
    if m:
        target = p._parse_sicoob_amount(m.group(1) + m.group(2))
        diff = current_bal - target
        print(f"Page {i+1} END: Calc {current_bal:.2f}, Target {target:.2f}, Diff {diff:.2f} | TxCount: {len(txns)}")
        # Reset to target
        current_bal = target
    elif (i+1) % 10 == 0:
        print(f"Page {i+1} (No balance) | Calc {current_bal:.2f} | TxCount: {len(txns)}")

print(f"Final Calc: {current_bal:.2f}")
