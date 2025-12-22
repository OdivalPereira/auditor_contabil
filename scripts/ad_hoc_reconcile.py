
import pandas as pd
import pdfplumber
import os
import re
from datetime import timedelta
import glob

# Configuration
DIARIO_PATH = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\diarios\CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv"
EXTRATOS_DIR = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extratos"
TOLERANCE_DAYS = 3

def parse_ledger(file_path):
    print(f"Parsing Ledger: {file_path}")
    # Adjust delimiter/encoding if necessary based on file inspection
    try:
        # Read with header=None, skip metadata lines
        # on_bad_lines='warn' will skip and print warnings
        df = pd.read_csv(file_path, sep=';', encoding='latin1', skiprows=4, header=None, on_bad_lines='warn', engine='python') 
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return pd.DataFrame()

    print("DEBUG: Ledger loaded with shape:", df.shape)
    # Rename columns by index
    # 2: Data, 11: Valor, 15: Historico, 13: Doc? (Let's check 13 later if needed, assuming 15 is Hist)
    # Based on previous output, Col 15 was "0000 13105..." which looks like Hist + Doc combined or Hist.
    
    # Map known columns
    mapping = {2: 'Data', 11: 'Valor', 15: 'Historico'}
    df.rename(columns=mapping, inplace=True)
    
    if 'Valor' in df.columns:
        # Remove thousands separator and fix decimal
        # Format: '      7255.70' (already dots?) or '1.000,00'?
        # The debug output showed '      7255.70'. This looks like standard float format?
        # Or maybe it has comma?
        # Let's clean safely.
        df['Valor_Float'] = df['Valor'].astype(str).str.replace(' ', '')
        # If it has comma as decimal:
        if df['Valor_Float'].str.contains(',', regex=False).any():
             df['Valor_Float'] = df['Valor_Float'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        
        df['Valor_Float'] = pd.to_numeric(df['Valor_Float'], errors='coerce')
        
    # Clean Date
    df['Date_Obj'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
    
    return df

def parse_bank_statements(pdf_dir):
    print(f"Parsing Bank Statements in: {pdf_dir}")
    all_txs = []
    
    pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
    for pdf_file in pdf_files:
        print(f"  Processing {os.path.basename(pdf_file)}...")
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                # Basic BB regex parser
                # Date | Description | Doc | Value | Type (D/C)
                # BB format usually: 
                # 01/05/2025 Some Description 12345 1.000,00 D
                
                # Regex for line starting with Date DD/MM/YYYY or DD/MM
                lines = text.split('\n')
                for line in lines:
                    # Generic implementation for BB
                    # Match date at start
                    match = re.match(r'^(\d{2}/\d{2}(?:/\d{4})?)\s+(.+?)\s+(-?[\d\.]+,\d{2})\s?([DC])?$', line)
                    if match:
                        dt_str, desc, val_str, dc = match.groups()
                        
                        # Parse Value
                        val = float(val_str.replace('.', '').replace(',', '.'))
                        if dc == 'D' or (dc is None and val_str.startswith('-')):
                            val = -abs(val)
                        else:
                            val = abs(val)
                            
                        # Parse Date (append current year if missing? The filename says 'Maio 2025')
                        # For safety, let's look for YYYY in file name or assume 2025 based on Sample
                        if len(dt_str) <= 5:
                            dt_str += "/2025" # TODO: Improve year detection
                            
                        all_txs.append({
                            'Date': dt_str,
                            'Description': desc.strip(),
                            'Value': val,
                            'Doc': '', # doc extraction can be tricky if mixed in description
                            'Source': os.path.basename(pdf_file)
                        })
                        
    return pd.DataFrame(all_txs)

def reconcile(df_ledger, df_bank):
    print("Reconciling...")
    
    # Convert dates
    df_bank['Date_Obj'] = pd.to_datetime(df_bank['Date'], dayfirst=True, errors='coerce')
    
    # Prepare easy lists
    ledger_items = df_ledger.copy()
    ledger_items['matched'] = False
    
    bank_items = df_bank.copy()
    bank_items['matched'] = False
    
    # Matching Logic
    # 1. Exact Match (Date + Amount)
    # 2. Tolerance Match (Date +/- 3 days + Amount)
    # 3. Many-to-One (Sum of Ledger = Bank Item) - Omitted for MVP/Speed, but easy to add if needed.
    
    matches = []
    
    for b_idx, b_row in bank_items.iterrows():
        b_amt = b_row['Value']
        b_date = b_row['Date_Obj']
        
        # Candidate Ledger Items
        # Filter unmatched
        candidates = ledger_items[~ledger_items['matched']]
        
        # Filter Date Tolerance
        candidates = candidates[
            (candidates['Date_Obj'] >= b_date - timedelta(days=TOLERANCE_DAYS)) & 
            (candidates['Date_Obj'] <= b_date + timedelta(days=TOLERANCE_DAYS))
        ]
        
        # Filter Amount (Direct or Inverted Sign?)
        # Bank Debit (-100) matches Accounting Credit (100 or -100 depending on storage)
        # Let's assume accounting 'Valor_Float' is absolute or signed.
        # If 'Valor_Float' is all positive, we need to match abs(b_amt).
        # Safe bet: Match ABS values for now, verify direction later?
        # User said: "Cruzamento de dados... comparando Valor e Data"
        
        # Let's try exact value match first
        match_candidate = candidates[candidates['Valor_Float'] == b_amt]
        
        if match_candidate.empty:
            # Try inverted sign
            match_candidate = candidates[candidates['Valor_Float'] == -b_amt]
            
        if match_candidate.empty:
             # Try absolute match
            match_candidate = candidates[candidates['Valor_Float'].abs() == abs(b_amt)]

        if not match_candidate.empty:
            # Take the first one (Date closest?)
            best_match = match_candidate.iloc[0]
            
            # Record Match
            matches.append({
                'Bank_Idx': b_idx,
                'Ledger_Idx': best_match.name,
                'Amount': b_amt,
                'Date_Bank': b_date,
                'Date_Ledger': best_match['Date_Obj']
            })
            
            # Mark matched
            bank_items.at[b_idx, 'matched'] = True
            ledger_items.at[best_match.name, 'matched'] = True
            
    return ledger_items, bank_items, pd.DataFrame(matches)

def main():
    # 1. Parse Ledger
    df_diario = parse_ledger(DIARIO_PATH)
    if not df_diario.empty:
        print(f"Ledger loaded: {len(df_diario)} rows")
    else:
        print("Failed to load Ledger.")
        return

    # 2. Parse Bank
    df_extrato = parse_bank_statements(EXTRATOS_DIR)
    if not df_extrato.empty:
        print(f"Bank Statements loaded: {len(df_extrato)} rows")
    else:
        print("Failed to load Bank Statements.")
        return
        
    # 3. Reconcile
    ledger_final, bank_final, matches = reconcile(df_diario, df_extrato)
    
    print(f"Matched: {len(matches)} items")
    
    # 4. Report
    # Divergences
    not_in_ledger = bank_final[~bank_final['matched']]
    not_in_bank = ledger_final[~ledger_final['matched']]
    
    print(f"Not in Ledger (Pendencies): {len(not_in_ledger)}")
    print(f"Not in Bank (Errors/Timing): {len(not_in_bank)}")
    
    # Save
    not_in_ledger.to_csv('divergences_not_in_ledger.csv', index=False)
    not_in_bank.to_csv('divergences_not_in_bank.csv', index=False)
    print("Reports saved: divergences_not_in_ledger.csv, divergences_not_in_bank.csv")

if __name__ == "__main__":
    main()
