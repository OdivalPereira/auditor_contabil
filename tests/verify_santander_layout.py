
import logging
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil")

try:
    from src.parsing.banks.santander import SantanderPDFParser
except ImportError:
    sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\src")
    from parsing.banks.santander import SantanderPDFParser

def test_santander_extraction():
    logging.basicConfig(level=logging.INFO)
    
    pdf_dir = Path(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extração_pdfs\pdf_modelos")
    files = [
        "Extrato Santander.pdf",
        "Santander 06.2024.pdf",
        "Santander 10.2025.pdf",
        "santander_05_24.pdf"
    ]
    
    parser = SantanderPDFParser()
    
    for filename in files:
        file_path = pdf_dir / filename
        print(f"\n{'='*50}")
        print(f"Testing: {filename}")
        print(f"{'='*50}")
        
        try:
            df, metadata = parser.parse(str(file_path))
            
            print(f"Rows extracted: {len(df)}")
            
            if not df.empty:
                print("\nSample Data (Head):")
                print(df.head())
                # Check for nulls
                nulls = df[['date', 'amount', 'description']].isnull().sum()
                if nulls.any():
                    print("\nWARNING: Null values found!")
                    print(nulls)
            else:
                print("\nFAILED: No data extracted!")
                
        except Exception as e:
            print(f"\nERROR parsing file: {e}")

if __name__ == "__main__":
    test_santander_extraction()
