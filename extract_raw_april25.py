"""
Extract raw PDF text near 25/04 to debug duplicate extraction
"""
import pdfplumber

pdf_path = 'extratos/BB 04 2025.pdf'

print("=" * 80)
print("RAW PDF TEXT EXTRACTION - April 25, 2025")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    for page_num, page in enumerate(pdf.pages, 1):
        text = page.extract_text() or ""
        
        # Check if this page has the date 25/04/2025
        if "25/04/2025" in text:
            print(f"\n\nPage {page_num} contains 25/04/2025:")
            print("─" * 80)
            
            # Extract lines around that date
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if "25/04/2025" in line:
                    # Print context: 3 lines before and 3 lines after
                    start = max(0, i - 3)
                    end = min(len(lines), i + 4)
                    
                    print(f"\nContext around line {i}:")
                    for j in range(start, end):
                        marker = ">>> " if j == i else "    "
                        print(f"{marker}[{j}] {lines[j]}")

print("\n" + "=" * 80 + "\n")
