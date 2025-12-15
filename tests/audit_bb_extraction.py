
import sys
import re
import pandas as pd
from pathlib import Path
from pypdf import PdfReader

# Add project root to path
sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil")

try:
    from src.parsing.banks.bb import BBMonthlyPDFParser
except ImportError:
    sys.path.append(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\src")
    from parsing.banks.bb import BBMonthlyPDFParser

def audit_extraction():
    pdf_dir = Path(r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extração_pdfs\pdf_modelos")
    files = [
        "Extrato Banco do Brasil  Janeiro 2025.pdf",
        "Extrato Banco do Brasil - Novembro 2025.pdf",
        "Contabilizado_Banco do Brasil 06.2025.pdf"
    ]
    
    parser = BBMonthlyPDFParser()
    
    # Loose pattern to identify anything that LOOKS like a transaction line
    # Date at start is the strongest signal
    potential_txn_pattern = re.compile(r"^\d{2}/\d{2}(?:/\d{4})?.*")
    
    for filename in files:
        file_path = pdf_dir / filename
        print(f"\n{'='*60}")
        print(f"AUDITING: {filename}")
        print(f"{'='*60}")
        
        # 1. Get Raw Lines that look like transactions
        raw_candidates = []
        reader = PdfReader(str(file_path))
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
                
        lines = full_text.split('\n')
        for line in lines:
            line = line.strip()
            # Filter out known non-transaction lines with dates (like headers sometimes)
            if potential_txn_pattern.match(line):
                # Ignore lines that are clearly period definitions or generation dates
                if "Extrato conta corrente" in line or "Período do" in line or "Saldo Anterior" in line:
                    continue
                raw_candidates.append(line)
        
        print(f"Potential Transaction Lines Found: {len(raw_candidates)}")
        
        # 2. Run Official Extraction
        try:
            df, _ = parser.parse(str(file_path))
            print(f"Parsed Transactions: {len(df)}")
            
            # 3. Compare
            print(f"SUMMARY: Raw Candidates: {len(raw_candidates)} vs Parsed: {len(df)}")
            
            if len(raw_candidates) != len(df):
                print(f"WARNING: Count mismatch in {filename}!")
                print("--- UNMATCHED RAW LINES (Potential Missing Transactions) ---")
                # Create a set of "signature" strings from parsed data for approximate matching
                # Signature: date_str + first_word_of_desc + value_int
                parsed_sigs = set()
                if not df.empty:
                    for _, row in df.iterrows():
                        # Create a simple signature
                        d = row['date'].strftime("%d/%m/%Y")
                        val = int(abs(row['amount'])) # integer part only
                        desc_start = row['description'].split()[0] if row['description'] else ""
                        parsed_sigs.add(f"{d}-{val}")

                count = 0
                for rc in raw_candidates:
                    # Parse loosely
                    # Try to find date and amount in rc line
                    # 03/01/2025 ... 406,34
                    
                    # split by space
                    parts = rc.split()
                    if len(parts) < 3: continue
                    
                    # date is parts[0] ?
                    date_part = parts[0]
                    # value is likely near end?
                    # This is just a heuristic to see what we are missing
                    
                    print(f" [MISSING?] {rc}")
                    count += 1
                    if count > 15: 
                        print(" ... (truncating) ...")
                        break
            else:
                print(f"SUCCESS: {filename} - Counts match ({len(df)}). Verified.")
                
            # 4. Spot check specifically for 'Contabilizado' oddities
            if "Contabilizado" in filename and df.empty:
                print("CRITICAL: Contabilizado extracted 0 rows!")
                print("Raw text dump of first 20 lines:")
                for l in lines[:20]: print(l)

        except Exception as e:
            print(f"Extraction Error: {e}")


if __name__ == "__main__":
    # Redirect stdout to a file
    with open("audit_results.txt", "w", encoding="utf-8") as f:
        sys.stdout = f
        audit_extraction()
        sys.stdout = sys.__stdout__
    print("Audit complete. Results in audit_results.txt")
