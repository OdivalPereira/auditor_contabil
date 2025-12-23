import pdfplumber
import re

pdf = pdfplumber.open('extratos/Extrato Stones 03 2025.pdf')
page = pdf.pages[5]
text = page.extract_text()
lines = text.split('\n')

date_pat = re.compile(r'^\d{2}/\d{2}/\d{2}\s')

print('First 40 lines from page 5 (checking which have dates):')
print('='*80)

for i, line in enumerate(lines[:40]):
    stripped = line.strip()
    has_date = '✓DATE' if date_pat.match(stripped) else '     '
    has_pix = '[PIX]' if 'pix' in stripped.lower() and 'maqu' in stripped.lower() else '     '
    print(f'{i:3} {has_date} {has_pix} |{stripped}|')

print('\n' + '='*80)
print('ANALYSIS:')
print('='*80)

# Count lines with dates
lines_with_dates = [i for i, line in enumerate(lines) if date_pat.match(line.strip())]
lines_with_pix_no_date = [i for i, line in enumerate(lines) if 'pix' in line.lower() and 'maqu' in line.lower() and not date_pat.match(line.strip())]
lines_with_pix_and_date = [i for i, line in enumerate(lines) if 'pix' in line.lower() and 'maqu' in line.lower() and date_pat.match(line.strip())]

print(f"Lines starting with date pattern: {len(lines_with_dates)}")
print(f"Lines with 'Pix|Maquininha' but NO date: {len(lines_with_pix_no_date)}")
print(f"Lines with 'Pix|Maquininha' AND date: {len(lines_with_pix_and_date)}")

if lines_with_pix_and_date:
    print(f"\nWARNING: Found {len(lines_with_pix_and_date)} lines with both Pix|Maquininha and date!")
    print("These should NOT exist according to user. Showing first 5:")
    for idx in lines_with_pix_and_date[:5]:
        print(f"  Line {idx}: |{lines[idx].strip()}|")
