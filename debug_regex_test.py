
import pdfplumber
import re
import os

def test_regex():
    pdf_dir = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extração_pdfs\pdf_modelos"
    filename = "Extrato Banco do Brasil  Janeiro 2025.pdf"
    path = os.path.join(pdf_dir, filename)
    
    # Updated Regex
    pattern = re.compile(
        r"^(\d{2}/\d{2}/\d{4})\s+"        # Date
        r"[\d\s\-X]+?\s+"                 # Junk numbers (Ag/Lote/Hist)
        r"(.+?)\s+"                       # Description (Lazy)
        r"([^\s]+)\s+"                    # Document (No spaces)
        r"([\d\.]+,\d{2})\s+"             # Value
        r"([DC])"                         # Type
    )
    
    print(f"Testing {filename}...")
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if not line: continue
                # Skip irrelevant
                if "Saldo Anterior" in line or "S A L D O" in line: continue
                
                # Check for date start
                if re.match(r"^\d{2}/\d{2}/\d{4}", line):
                    match = pattern.match(line)
                    if match:
                        print(f"[MATCH] {line[:50]}...")
                    else:
                        print(f"[FAIL ] {line}")

if __name__ == "__main__":
    test_regex()
