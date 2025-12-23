import pdfplumber
import re

pdf_path = 'extratos/Extrato Stones 03 2025.pdf'
with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text and 'Maikon Dias Leal' in text:
            print(f"--- PAGE {page_num + 1} ---")
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if 'Maikon Dias Leal' in line:
                    # Print context
                    for j in range(max(0, i-5), min(len(lines), i+10)):
                        print(f"{j:3}: {lines[j]}")
            break
