import pdfplumber
import re
from datetime import datetime

f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
pdf = pdfplumber.open(f)
page = pdf.pages[22]  # Page 23

words = page.extract_words()
lines_data = {}
for w in words:
    top = int(w['top'] // 2) * 2
    lines_data.setdefault(top, []).append(w)


sorted_tops = sorted(lines_data.keys())

# Find line with SALDO DO DIA
for top in sorted_tops:
    line_words = sorted(lines_data[top], key=lambda x: x['x0'])
    line_text = " ".join([w['text'] for w in line_words]).strip()
    upper_text = line_text.upper()
    
    if "SALDO DO DIA" in upper_text:
        print(f"Found SALDO DO DIA line at top={top}")
        print(f"Line text: {line_text}")
        print(f"Upper text: {upper_text}")
        print(f"'SALDO' in upper_text: {'SALDO' in upper_text}")
        print(f"'TOTAL' in upper_text: {'TOTAL' in upper_text}")
        
        # Check if it would skip
        if "SALDO" in upper_text or "TOTAL" in upper_text:
            print("SHOULD SKIP: Yes")
        else:
            print("SHOULD SKIP: No")
            
        # Check money tokens
        nums = []
        for w in line_words:
            txt = w['text']
            if re.search(r'[\d\.,]+[CD\*]$', txt):
                nums.append((txt, w['x0']))
        print(f"Money tokens found: {nums}")
        print(f"is_money_line check: {any(300 < n[1] < 530 for n in nums)}")
        print()
