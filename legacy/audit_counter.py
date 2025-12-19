
import os
import sys
import pandas as pd

ROOT = r"c:\Users\contabil/Documents/Projetos Antigravity/auditor_contabil"
sys.path.append(ROOT)
from src.parsing.banks.bb import BBMonthlyPDFParser

parser = BBMonthlyPDFParser()
path = os.path.join(ROOT, "extratos/01 2025/Extrato BB 01 2025.pdf")

# We want to see the count BEFORE drop_duplicates()
# But the parser does it inside. We'll check the source code again.
with open(os.path.join(ROOT, "src/parsing/banks/bb.py"), "r") as f:
    code = f.read()

# I'll manually run the loop for a few lines
import re
pattern = re.compile(
    r"^(\d{2}/\d{2}/\d{4})\s+"        # Date
    r"[\d\s\-X]+?\s+"                 # Junk numbers
    r"(.+?)\s+"                       # Description
    r"([^\s]+)\s+"                    # Document
    r"([\d\.]+,\d{2})\s+"             # Value
    r"([DC])"                         # Type
    r"(?:\s+[\d\.]+,\d{2}\s+[DC])?$" # Optional Balance
)

import pdfplumber
count = 0
matches = []
total_sum = 0.0
with pdfplumber.open(path) as pdf:
    for page in pdf.pages:
        text = page.extract_text()
        if not text: continue
        for line in text.split('\n'):
            line = line.strip()
            m = pattern.match(line)
            if m:
                count += 1
                val_str = m.group(4)
                dc = m.group(5)
                val = float(val_str.replace('.', '').replace(',', '.'))
                if dc == 'D': val = -val
                total_sum += val

print(f"Total Matches: {count}")
print(f"Total Sum of all matches: {total_sum:.2f}")
