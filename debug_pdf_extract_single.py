
import pdfplumber
import os

pdf_dir = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extração_pdfs\pdf_modelos"
files = [
    "Contabilizado_Banco do Brasil 06.2025.pdf"
]

for filename in files:
    path = os.path.join(pdf_dir, filename)
    print(f"\n--- Extracting {filename} ---")
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:1]: 
                text = page.extract_text()
                print(text)
    except Exception as e:
        print(f"Error reading {filename}: {e}")
