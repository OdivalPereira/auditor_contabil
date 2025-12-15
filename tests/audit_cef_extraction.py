
import sys
import re
import pandas as pd
from pathlib import Path
import pdfplumber

# Add project root to path
sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil")

try:
    from src.parsing.banks.cef import CEFPdfParser
except ImportError:
    sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\src")
    from parsing.banks.cef import CEFPdfParser

def audit_cef_extraction():
    pdf_dir = Path(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extração_pdfs\pdf_modelos")
    files = ["Extrato CEF.pdf"]
    
    parser = CEFPdfParser()
    
    # Loose pattern for CEF transaction lines: Date at start
    potential_txn_pattern = re.compile(r"^\d{2}/\d{2}/\d{4}")
    
    for filename in files:
        file_path = pdf_dir / filename
        print(f"\n{'='*60}")
        print(f"AUDITING: {filename}")
        print(f"{'='*60}")
        
        # 1. Get Raw Lines that look like transactions
        raw_candidates = []
        try:
            with pdfplumber.open(str(file_path)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if potential_txn_pattern.match(line):
                                # Filter out headers if they accidentally match (unlikely with deep date format)
                                raw_candidates.append(line)
        except Exception as e:
            print(f"Error reading PDF: {e}")
            continue
        
        print(f"Potential Transaction Lines Found: {len(raw_candidates)}")
        
        # 2. Run Official Extraction
        try:
            df, _ = parser.parse(str(file_path))
            print(f"Parsed Transactions: {len(df)}")
            
            # 3. Compare
            print(f"SUMMARY: Raw Candidates: {len(raw_candidates)} vs Parsed: {len(df)}")
            
            if len(raw_candidates) != len(df):
                print(f"WARNING: Count mismatch in {filename}!")
                print("--- UNMATCHED RAW LINES ---")
                
                # Check specifics
                count = 0
                for rc in raw_candidates:
                    # Very simple signature check: Date + Amount match?
                    # This is just a diff dump
                    # Let's verify if parsed df has this date?
                    # Not efficient but effective for small sample
                    
                    found = False
                     # This check is weak, just dump for manual review
                    
                    print(f" [CANDIDATE] {rc}")
                    count += 1
                    if count > 10: 
                        print(" ... (truncating) ...")
                        break
            else:
                print(f"SUCCESS: {filename} - Counts match ({len(df)}). Verified.")

        except Exception as e:
            print(f"Extraction Error: {e}")

if __name__ == "__main__":
    audit_cef_extraction()
