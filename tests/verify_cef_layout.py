
import logging
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil")

try:
    from src.parsing.banks.cef import CEFPdfParser
except ImportError:
    sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\src")
    from parsing.banks.cef import CEFPdfParser

def test_cef_extraction():
    logging.basicConfig(level=logging.INFO)
    
    pdf_dir = Path(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extração_pdfs\pdf_modelos")
    files = [
        "Extrato CEF.pdf"
    ]
    
    parser = CEFPdfParser()
    
    for filename in files:
        file_path = pdf_dir / filename
        print(f"\n{'='*50}")
        print(f"Testing: {filename}")
        print(f"{'='*50}")
        
        try:
            df, metadata = parser.parse(str(file_path))
            
            print(f"Metadata: {metadata}")
            print(f"Rows extracted: {len(df)}")
            
            if not df.empty:
                print("\nSample Data (Head):")
                print(df.head())
                print("\nSample Data (Tail):")
                print(df.tail())
                
                # Check for nulls in critical fields
                nulls = df[['date', 'amount', 'description']].isnull().sum()
                if nulls.any():
                    print("\nWARNING: Null values found!")
                    print(nulls)
            else:
                print("\nFAILED: No data extracted!")
                # Debug raw text
                import pdfplumber
                with pdfplumber.open(str(file_path)) as pdf:
                    print("RAW TEXT SAMPLE (Page 1):")
                    print(pdf.pages[0].extract_text()[:1000])
                
        except Exception as e:
            print(f"\nERROR parsing file: {e}")

if __name__ == "__main__":
    test_cef_extraction()
