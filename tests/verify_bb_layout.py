
import logging
import pandas as pd
from pathlib import Path
import sys

# Add src to path
# Add project root to path
sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil")

try:
    from src.parsing.banks.bb import BBMonthlyPDFParser
except ImportError:
    # Fallback if src is already in path implicitely or differently
    sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\src")
    from parsing.banks.bb import BBMonthlyPDFParser

def test_bb_extraction():
    logging.basicConfig(level=logging.INFO)
    
    pdf_dir = Path(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extração_pdfs\pdf_modelos")
    files = [
        "Extrato Banco do Brasil  Janeiro 2025.pdf",
        "Extrato Banco do Brasil - Novembro 2025.pdf",
        "Contabilizado_Banco do Brasil 06.2025.pdf"
    ]
    
    parser = BBMonthlyPDFParser()

    for filename in files:
        file_path = pdf_dir / filename
        try:
            df, metadata = parser.parse(str(file_path))
            if not df.empty:
                print(f"PASS: {filename} - Extracted {len(df)} rows.")
            else:
                print(f"FAIL: {filename} - Extracted 0 rows.")
        except Exception as e:
            print(f"ERROR: {filename} - {e}")

if __name__ == "__main__":
    test_bb_extraction()
