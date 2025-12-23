import re
from datetime import datetime

def _parse_br_amount(val_s):
    val_s = val_s.replace('R$', '').replace(' ', '')
    val_s = val_s.replace('.', '').replace(',', '.')
    try:
        return float(val_s)
    except:
        return 0.0

lines = [
    "STONE INSTITUIÇÃO",
    "Recebimento vendas DE PAGAMENTO S.A.",
    "03/03/2025 Crédito 43,65 8.497,16",
    "Antecipação Agência 0001",
    "Conta 30772-8",
    "STONE INSTITUIÇÃO",
    "Recebimento vendas DE PAGAMENTO S.A.",
    "03/03/2025 Crédito 43,65 8.453,51",
    "Antecipação Agência 0001",
    "Conta 30772-8"
]

date_pattern = re.compile(r'^(\d{2}/\d{2}(?:/\d{2,4})?)(\s|$)')
txn_pattern_full = re.compile(r'^(\d{2}/\d{2}(?:/\d{2,4})?)\s+(E\w+|S\w+|Cr.dito|D.bito)\s+(.*?)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$', re.IGNORECASE)
txn_pattern_short = re.compile(r'^(\d{2}/\d{2}(?:/\d{2,4})?)\s+(E\w+|S\w+|Cr.dito|D.bito)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$', re.IGNORECASE)

anchors = []
for idx, line in enumerate(lines):
    if date_pattern.match(line):
        anchors.append(idx)
print(f"Anchors identified: {anchors}")

rows = []
consumed_lines = set()

for anchor_idx in anchors:
    line = lines[anchor_idx]
    m = txn_pattern_full.search(line)
    desc = ""
    if not m:
        m = txn_pattern_short.search(line)
        if not m:
            print(f"Anchor {anchor_idx} failed regex match!")
            continue
        dt_s, ttype, val_s, bal_s = m.groups()
    else:
        dt_s, ttype, desc, val_s, bal_s = m.groups()
    
    print(f"Processing Anchor {anchor_idx}: {line}")
    is_tariff = 'tarifa' in desc.lower() or 'tarifa' in ttype.lower()
    block_lines = []
    
    # 1. Look UP
    if not is_tariff and anchor_idx > 0:
        prev_idx = anchor_idx - 1
        if prev_idx not in anchors and prev_idx not in consumed_lines:
            if not re.search(r'\d{2,},\d{2}', lines[prev_idx]):
                block_lines.append(lines[prev_idx])
                consumed_lines.add(prev_idx)
    
    # 2. Add CORE
    block_lines.append(line)
    consumed_lines.add(anchor_idx)
    
    # 3. Look DOWN
    if not is_tariff:
        for offset in [1, 2]:
            next_idx = anchor_idx + offset
            if next_idx < len(lines) and next_idx not in anchors and next_idx not in consumed_lines:
                if not re.search(r'\d{2,},\d{2}', lines[next_idx]):
                    block_lines.append(lines[next_idx])
                    consumed_lines.add(next_idx)
                else: break
            else: break
            
    full_desc = " ".join(block_lines).strip()
    rows.append({'amount': _parse_br_amount(val_s), 'desc': full_desc})

print(f"\nFinal Rows Extracted ({len(rows)}):")
for r in rows:
    print(r)
