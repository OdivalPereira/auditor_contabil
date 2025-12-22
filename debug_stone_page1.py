import pdfplumber
import re
from src.parsing.banks.stone import StonePDFParser

f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
pdf = pdfplumber.open(f)

# Get FIRST page in PDF (which is last chronologically - 31/05)
page1 = pdf.pages[0]
text = page1.extract_text()
lines = text.split('\n')

print("="*80)
print("LAST PAGE (31/05 - First in PDF) - Line-by-line extraction")
print("="*80)

# Pattern: 31/05/25 Saída Tarifa - R$ 0,44 R$ 2.313,21
txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{2})\s+(Entrada|Saída)\s*(.*?)\s*(-?)\s*R\$\s*([\d\.,]+)\s+(-?)\s*R\$\s*([\d\.,]+)")

manual_txns = []
for i, line in enumerate(lines):
    m = txn_pattern.search(line)
    if m:
        dt_s, ttype, desc, v_sign, val_s, b_sign, bal_s = m.groups()
        # Parse amount
        val_clean = val_s.replace('.', '').replace(',', '.')
        try:
            amount = float(val_clean)
            if v_sign == '-' or ttype == 'Saída':
                amount = -abs(amount)
            else:
                amount = abs(amount)
            
            # Parse balance
            bal_clean = bal_s.replace('.', '').replace(',', '.')
            balance = float(bal_clean)
            if b_sign == '-':
                balance = -abs(balance)
            
            is_tarifa = 'Tarifa' in desc or 'TARIFA' in desc.upper()
            
            manual_txns.append({
                'line': i,
                'date': dt_s,
                'type': ttype,
                'amount': amount,
                'balance': balance,
                'is_tarifa': is_tarifa,
                'desc_snippet': desc[:30]
            })
        except:
            pass

print(f"\nFound {len(manual_txns)} transactions on page 1")
print(f"Tarifas: {sum(1 for t in manual_txns if t['is_tarifa'])}")
print(f"Non-tarifas: {sum(1 for t in manual_txns if not t['is_tarifa'])}")

# Now extract using parser
p = StonePDFParser()
parser_rows, bs, be = p.extract_page(page1)
print(f"\nParser extracted: {len(parser_rows)} transactions")
print(f"Parser bs: {bs}, be: {be}")

# Compare
print("\n" + "="*80)
print("COMPARISON - First 10 non-tarifa transactions:")
print("="*80)
non_tarifa = [t for t in manual_txns if not t['is_tarifa']]
for i, t in enumerate(non_tarifa[:10]):
    print(f"{t['date']} {t['type']:7} {t['amount']:>10.2f} | Bal: {t['balance']:>10.2f} | {t['desc_snippet']}")

print("\n" + "="*80)
print("What parser captured (first 10):")
print("="*80)
for i, t in enumerate(parser_rows[:10]):
    print(f"{t['date']} {t['amount']:>10.2f} | {t['description'][:40]}")
