from src.parsing.banks.stone import StonePDFParser
import pdfplumber

parser = StonePDFParser()
with pdfplumber.open('extratos/Extrato Stones 03 2025.pdf') as pdf:
    page = pdf.pages[21] # Page 22
    rows, _, _ = parser.extract_page(page)
    print(f"Extracted {len(rows)} rows from Page 22")
    for r in rows:
        if 21.72 in [r['amount']]:
            print(r)
