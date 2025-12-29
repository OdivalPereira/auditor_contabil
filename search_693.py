"""
Search for all lines containing 693,24 in April PDF
"""
import pdfplumber

pdf_path = 'extratos/BB 04 2025.pdf'

print("=" * 80)
print("SEARCHING FOR 693,24 IN PDF")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        text = page.extract_text() or ""
        
        if "693,24" in text or "693.24" in text:
            print(f"\n\nPage {page_num} contains '693,24':")
            print("─" * 80)
            
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if "693,24" in line or "693.24" in line:
                    print(f"[{i}] {line}")

print("\n" + "=" * 80 + "\n")
