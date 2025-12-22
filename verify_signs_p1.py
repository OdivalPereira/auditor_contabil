import pdfplumber
import re
from src.parsing.banks.stone import StonePDFParser

f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
pdf = pdfplumber.open(f)
p = StonePDFParser()

page1 = pdf.pages[0]
text = page1.extract_text()
lines = text.split('\n')

txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{2})\s+(Entrada|Saída)\s*(.*?)\s*(-?)\s*R\$\s*([\d\.,]+)\s+(-?)\s*R\$\s*([\d\.,]+)")

print("="*80)
print("PAGE 1 - SIGN VERIFICATION")
print("="*80)
print("Checking if signs match between manual and parser extraction\n")

# Manual extraction with signs
manual_txns = []
for line in lines:
    m = txn_pattern.search(line)
    if m:
        dt_s, ttype, desc, v_sign, val_s, b_sign, bal_s = m.groups()
        is_tarifa = 'Tarifa' in desc or 'TARIFA' in desc.upper() or 'Tarifa' in line
        if not is_tarifa:
            val_clean = val_s.replace('.', '').replace(',', '.')
            amount = float(val_clean)
            if v_sign == '-' or ttype == 'Saída':
                amount = -abs(amount)
            else:
                amount = abs(amount)
            manual_txns.append((ttype, amount, desc[:20]))

# Parser extraction
parser_rows, _, _ = p.extract_page(page1)

print(f"{'Type':<10} {'Manual':>10} {'Parser':>10} {'Match':>8} Description")
print("-" * 80)

for i, (manual, parser_row) in enumerate(zip(manual_txns, parser_rows)):
    m_type, m_amount, m_desc = manual
    p_amount = parser_row['amount']
    match = "✓" if abs(m_amount - p_amount) < 0.01 else "✗"
    print(f"{m_type:<10} {m_amount:>10.2f} {p_amount:>10.2f} {match:>8} {m_desc}")

print("\n" + "="*80)
print("Sum comparison:")
manual_sum = sum(m[1] for m in manual_txns)
parser_sum = sum(r['amount'] for r in parser_rows)
print(f"Manual sum: {manual_sum:.2f}")
print(f"Parser sum: {parser_sum:.2f}")
print(f"Difference: {abs(manual_sum - parser_sum):.2f}")
print(f"Match: {'✓' if abs(manual_sum - parser_sum) < 0.01 else '✗'}")
