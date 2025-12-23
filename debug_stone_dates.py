import sys
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser
import pdfplumber

parser = StonePDFParser()
pdf_path = 'extratos/Extrato Stones 03 2025.pdf'
with pdfplumber.open(pdf_path) as pdf:
    # Page 41 (index 40)
    page = pdf.pages[40]
    rows, bal_start, bal_end = parser.extract_page(page)
    
    print(f"Extraction for {pdf_path} PAGE 41:")
    for row in rows:
        if 'Alex Rodrigues' in row['description']:
            print(f"FOUND: {row['date']} | {row['description']} | {row['amount']}")

# Also check Luana in February
pdf_path_feb = 'extratos/Extrato Stones 02 2025.pdf'
print("\nSearching for Luana in Feb...")
with pdfplumber.open(pdf_path_feb) as pdf:
    for i, page in enumerate(pdf.pages):
        rows, _, _ = parser.extract_page(page)
        for row in rows:
            if 'Luana' in row['description'] or '31,50' == str(row['amount']):
                 print(f"PG {i+1} FOUND: {row['date']} | {row['description']} | {row['amount']}")
            if 'CULHARI' in row['description'].upper():
                 print(f"PG {i+1} CULHARI FOUND: {row['date']} | {row['description']} | {row['amount']}")

