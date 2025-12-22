import pdfplumber
import re
from src.parsing.banks.stone import StonePDFParser

f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
pdf = pdfplumber.open(f)
p = StonePDFParser()

txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{2})\s+(Entrada|Saída)\s*(.*?)\s*(-?)\s*R\$\s*([\d\.,]+)\s+(-?)\s*R\$\s*([\d\.,]+)")

print("="*80)
print("PAGE-BY-PAGE COMPARISON (Manual vs Parser)")
print("="*80)

total_manual = 0
total_parser = 0

for page_num in range(min(10, len(pdf.pages))):  # First 10 pages
    page = pdf.pages[page_num]
    text = page.extract_text()
    lines = text.split('\n')
    
    # Manual count
    manual_non_tarifa = 0
    for line in lines:
        m = txn_pattern.search(line)
        if m:
            dt_s, ttype, desc, v_sign, val_s, b_sign, bal_s = m.groups()
            is_tarifa = 'Tarifa' in desc or 'TARIFA' in desc.upper() or 'Tarifa' in line
            if not is_tarifa:
                manual_non_tarifa += 1
    
    # Parser count
    parser_rows, bs, be = p.extract_page(page)
    parser_count = len(parser_rows)
    
    total_manual += manual_non_tarifa
    total_parser += parser_count
    
    match = "✓" if manual_non_tarifa == parser_count else "✗"
    print(f"Page {page_num+1:3}: Manual={manual_non_tarifa:3}, Parser={parser_count:3} {match}")
    
    if manual_non_tarifa != parser_count:
        print(f"  ⚠️  MISMATCH! Diff: {parser_count - manual_non_tarifa}")

print("\n" + "="*80)
print(f"TOTALS (first 10 pages):")
print(f"Manual: {total_manual}")
print(f"Parser: {total_parser}")
print(f"Difference: {total_parser - total_manual}")
