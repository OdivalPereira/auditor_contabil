import pdfplumber
import re
from src.parsing.banks.stone import StonePDFParser

f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
pdf = pdfplumber.open(f)
p = StonePDFParser()

# Count ALL pages manually
txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{2})\s+(Entrada|Saída)\s*(.*?)\s*(-?)\s*R\$\s*([\d\.,]+)\s+(-?)\s*R\$\s*([\d\.,]+)")

total_manual_non_tarifa = 0
total_manual_entradas = 0
total_manual_saidas = 0

print(f"Processing {len(pdf.pages)} pages...")

for page_num, page in enumerate(pdf.pages):
    text = page.extract_text()
    lines = text.split('\n')
    
    for line in lines:
        m = txn_pattern.search(line)
        if m:
            dt_s, ttype, desc, v_sign, val_s, b_sign, bal_s = m.groups()
            is_tarifa = 'Tarifa' in desc or 'TARIFA' in desc.upper() or 'Tarifa' in line
            if not is_tarifa:
                total_manual_non_tarifa += 1
                if ttype == 'Entrada':
                    total_manual_entradas += 1
                else:
                    total_manual_saidas += 1

# Parser totals
df, m = p.parse(f)

print("="*80)
print("FULL FILE COMPARISON")
print("="*80)
print(f"Manual count (all {len(pdf.pages)} pages):")
print(f"  Total non-tarifa: {total_manual_non_tarifa}")
print(f"  Entradas: {total_manual_entradas}")
print(f"  Saídas: {total_manual_saidas}")

print(f"\nParser count:")
print(f"  Total: {len(df)}")
print(f"  Entradas (+): {len(df[df.amount > 0])}")
print(f"  Saídas (-): {len(df[df.amount < 0])}")

print(f"\nMatch: {'✓' if total_manual_non_tarifa == len(df) else '✗'}")

if total_manual_non_tarifa != len(df):
    print(f"⚠️  MISMATCH: Parser has {len(df) - total_manual_non_tarifa} extra/missing transactions")
