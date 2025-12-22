import pdfplumber
import re
import os
from src.parsing.banks.sicoob import SicoobPDFParser

p = SicoobPDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
pdf = pdfplumber.open(f)

page = pdf.pages[22] # Page 23
print(f"--- Debugging Page 23 (Index 22) ---")

words = page.extract_words()
lines_data = {}
for w in words:
    top = int(w['top'] // 2) * 2
    lines_data.setdefault(top, []).append(w)

sorted_tops = sorted(lines_data.keys())
current_date = "N/A"

print(f"{'TOP':<6} | {'DATE':<10} | {'AMOUNT':>10} | {'DESCRIPTION'}")
print("-" * 80)

for top in sorted_tops:
    line_words = sorted(lines_data[top], key=lambda x: x['x0'])
    line_text = " ".join([w['text'] for w in line_words])
    
    # Date detection
    dt_words = [w['text'] for w in line_words if w['x0'] < 200]
    dt_s = "".join(dt_words)
    if re.match(r"\d{2}/\d{2}/\d{4}", dt_s):
        current_date = dt_s[:10]
        
    # Money detection
    nums = []
    for w in line_words:
        txt = w['text']
        if re.search(r'[\d\.,]+[CD\*]$', txt):
            nums.append((p._parse_sicoob_amount(txt), w['x0'], txt))
            
    is_money = any(300 < n[1] < 530 for n in nums)
    amt = 0
    if is_money:
        # Simplification of parser logic
        valid_nums = [n for n in nums if abs(n[0]) > 0.001]
        if len(valid_nums) >= 2:
            amt = valid_nums[-2][0] if valid_nums[-1][1] > 525 else valid_nums[-1][0]
        elif valid_nums:
            amt = valid_nums[0][0] if valid_nums[0][1] <= 525 else 0
            
    if is_money or "SALDO" in line_text.upper():
        print(f"{top:<6} | {current_date:<10} | {amt:>10.2f} | {line_text}")
