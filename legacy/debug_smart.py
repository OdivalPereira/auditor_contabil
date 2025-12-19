import pdfplumber
import re
from datetime import datetime
import pandas as pd

def _parse_br_amount(text):
    if not text: return 0.0
    text = text.replace('R$', '').replace('$', '').strip()
    text = text.replace('.', '').replace(',', '.')
    try: return float(text)
    except: return 0.0

def extract_transactions_smart(page):
    words = page.extract_words()
    lines = {}
    for w in words:
        top = int(w['top'] // 2) * 2
        if top not in lines: lines[top] = []
        lines[top].append(w)
        
    txns = []
    desc_buffer = []
    
    for top in sorted(lines.keys()):
        line_words = sorted(lines[top], key=lambda x: x['x0'])
        text = " ".join([w['text'] for w in line_words])
        print(f"DEBUG Line: {text}")
        
        date_match = re.search(r"(\d{2}[/\.]\d{2}[/\.]\d{4})", text)
        if not date_match:
            desc_buffer.append(text)
            continue
        
        date_str = date_match.group(1).replace(".", "/")
        try:
            dt = datetime.strptime(date_str, "%d/%m/%Y").date()
        except:
            print(f"  Failed date parse: {date_str}")
            continue
        
        amt_pattern = re.compile(r"(-?[\d\.]*,\d{2})\s*([CD])?")
        matches = list(amt_pattern.finditer(text))
        
        print(f"  Found {len(matches)} potential amounts")
        if len(matches) >= 1:
            amt_match = matches[-2] if len(matches) >= 2 else matches[0]
            val_s, dc = amt_match.groups()
            amount = _parse_br_amount(val_s)
            
            if "-" in val_s or dc == 'D' or any(k in text.upper() for k in ['DEBITO', 'PAGTO', 'ENVIADO', 'SAQU', 'TARIFA']):
                amount = -abs(amount)
            elif dc == 'C' or any(k in text.upper() for k in ['CREDITO', 'RECEBIDO', 'ESTORN', 'DEPOSITO']):
                amount = abs(amount)
            
            if amount != 0:
                description = " ".join(desc_buffer).strip()
                if not description: description = text
                txns.append({'date': dt, 'amount': amount, 'description': description})
                print(f"  TXN: {dt} | {amount} | {description}")
                desc_buffer = []
        else:
            desc_buffer.append(text)
            
    return txns

if __name__ == "__main__":
    path = "extração_pdfs/pdf_modelos/Extrato Santander.pdf"
    with pdfplumber.open(path) as pdf:
        res = extract_transactions_smart(pdf.pages[0])
        print(f"\nTOTAL TXNS: {len(res)}")
