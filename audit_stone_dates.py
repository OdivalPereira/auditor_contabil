import pdfplumber
import re
import os

date_re = re.compile(r'^(\d{2}/\d{2}(/\d{2,4})?)')

def audit_file(file_path):
    print(f"\n--- Auditing: {file_path} ---")
    if not os.path.exists(file_path):
        print("File not found.")
        return

    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            # Check last 3 lines
            for j, line in enumerate(lines[-3:]):
                line = line.strip()
                match = date_re.search(line)
                if match:
                    date_str = match.group(1)
                    if len(date_str) < 10:
                        print(f"PG {i+1} LOW YEAR: {line}")
            
            # Check if any line looks like a date prefix but failed the regex
            for line in lines:
                line = line.strip()
                if re.match(r'^\d{2}/\d{2}$', line) or re.match(r'^\d{2}/\d{2}/$', line):
                     print(f"PG {i+1} TRUNCATED DATE LINE: {line}")

audit_file('extratos/Extrato Stones 02 2025.pdf')
audit_file('extratos/Extrato Stones 03 2025.pdf')
