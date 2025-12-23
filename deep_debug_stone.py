import re
import pdfplumber

def _parse_br_amount(val_s):
    val_s = val_s.replace('R$', '').replace(' ', '')
    val_s = val_s.replace('.', '').replace(',', '.')
    return float(val_s)

pdf_path = 'extratos/Extrato Stones 03 2025.pdf'
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[40] # Page 41
    text = page.extract_text()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s')
    txn_pattern_full = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+(.*?)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$')
    txn_pattern_short = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$')

    anchors = []
    for idx, line in enumerate(lines):
        if date_pattern.match(line):
            anchors.append(idx)
            print(f"ANCHOR {idx}: {line}")
            m = txn_pattern_full.search(line)
            if m:
                print(f"  MATCH FULL: {m.groups()}")
            else:
                m = txn_pattern_short.search(line)
                if m:
                    print(f"  MATCH SHORT: {m.groups()}")
                else:
                    print(f"  NO MATCH")

    print("\nVerifying 'Alex Rodrigues' lines specifically:")
    for i, line in enumerate(lines):
        if 'Alex Rodrigues' in line or '30,00' in line:
            print(f"L{i}: {line}")

