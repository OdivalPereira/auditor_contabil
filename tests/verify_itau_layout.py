
import logging
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil")

try:
    from src.parsing.banks.itau import ItauPDFParser
except ImportError:
    sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\src")
    from parsing.banks.itau import ItauPDFParser

def test_itau_extraction():
    logging.basicConfig(level=logging.INFO)
    
    pdf_dir = Path(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extração_pdfs\pdf_modelos")
    files = [
        "Extrato Sagrado 10 2025 itau.pdf",
        "extrato_itau_02_25.pdf",
        "extrato_itau_03_25.pdf"
    ]
    
    parser = ItauPDFParser()
    
    for filename in files:
        file_path = pdf_dir / filename
        print(f"\n{'='*50}")
        print(f"Testing: {filename}")
        print(f"{'='*50}")
        
        try:
            df, metadata = parser.parse(str(file_path))
            
            print(f"Rows extracted: {len(df)}")
            if metadata.get('start_date'):
                 print(f"Metadata Period: {metadata['start_date']} to {metadata['end_date']}")
            
            if not df.empty:
                print("\nSample Data (Head):")
                print(df.head())
                print("\nSample Descriptions:")
                for d in df['description'].head(10):
                    print(f" - {d}")
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
    test_itau_extraction()
