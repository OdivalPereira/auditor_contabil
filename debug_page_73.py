import re
import pdfplumber
from datetime import datetime

def _parse_br_amount(val_s):
    val_s = val_s.replace('R$', '').replace(' ', '')
    val_s = val_s.replace('.', '').replace(',', '.')
    try:
        return float(val_s)
    except:
        return 0.0

pdf_path = 'extratos/Extrato Stones 02 2025.pdf'
with pdfplumber.open(pdf_path) as pdf:
    page = pdf.pages[72] # Page 73
    text = page.extract_text()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    print("--- ALL LINES ---")
    for i, line in enumerate(lines):
        print(f"{i}: {line}")
    print("-----------------\n")

    date_pattern = re.compile(r'^(\d{2}/\d{2}(?:/\d{2,4})?)(\s|$)')
    txn_pattern_full = re.compile(r'^(\d{2}/\d{2}(?:/\d{2,4})?)\s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+(.*?)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$')
    txn_pattern_short = re.compile(r'^(\d{2}/\d{2}(?:/\d{2,4})?)\s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$')

    anchors = []
    for idx, line in enumerate(lines):
        if date_pattern.match(line):
            anchors.append(idx)
            print(f"ANCHOR {idx}: {line}")

    consumed_lines = set()
    extracted = []
    
    for anchor_idx in anchors:
        line = lines[anchor_idx]
        m = txn_pattern_full.search(line)
        desc = ""
        if not m:
            m = txn_pattern_short.search(line)
            if not m:
                print(f"  FAILED MATCH: {line}")
                continue
            dt_s, ttype, val_s, bal_s = m.groups()
        else:
            dt_s, ttype, desc, val_s, bal_s = m.groups()
            
        is_tariff = 'tarifa' in desc.lower() or 'tarifa' in ttype.lower()
        block_lines = []
        
        # Look UP
        if not is_tariff and anchor_idx > 0:
            prev_idx = anchor_idx - 1
            if prev_idx not in anchors and prev_idx not in consumed_lines:
                if not re.search(r'\d{2,},\d{2}', lines[prev_idx]):
                    print(f"  Consumed UP {prev_idx}: {lines[prev_idx]}")
                    block_lines.append(lines[prev_idx])
                    consumed_lines.add(prev_idx)
        
        # Current
        print(f"  Core {anchor_idx}: {line}")
        block_lines.append(line)
        consumed_lines.add(anchor_idx)
        
        # Look DOWN
        if not is_tariff and anchor_idx < len(lines) - 1:
            next_idx = anchor_idx + 1
            if next_idx not in anchors and next_idx not in consumed_lines:
                print(f"  Consumed DOWN {next_idx}: {lines[next_idx]}")
                block_lines.append(lines[next_idx])
                consumed_lines.add(next_idx)
        
        extracted.append(block_lines)

    print("\n--- FINAL EXTRACTED BLOCKS ---")
    for block in extracted:
        print(f"Block: {block}")
