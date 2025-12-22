
import pandas as pd
import sys
import os
from datetime import timedelta

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.core.reconciler import Reconciler
from src.core.matcher import CombinatorialMatcher
from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator
import glob

# Configuration
DIARIO_PATH = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\diarios\CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv"
EXTRATOS_DIR = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extratos"
TOLERANCE_DAYS = 3

def run_app_logic():
    print("--- Running Existing App Logic ---")
    
    # 1. Parse Ledger (Mimicking conciliator_app.py lines 279-293)
    print(f"Loading Ledger: {DIARIO_PATH}")
    try:
        # App logic: pd.read_csv directly
        # Note: conciliator_app.py doesn't specify separator or encoding for CSV, 
        # so it uses default (sep=',', encoding='utf-8'). 
        # This will likely fail or produce 1 column if sep is ';'.
        # I will strictly mimic the app's code: `df_ledger = pd.read_csv(ledger_file)`
        # But `ledger_file` in app is a Streamlit UploadedFile (BytesIO). 
        # Here it is a path. `pd.read_csv` handles paths.
        
        # STRICT MIMIC: The app uses `pd.read_csv(ledger_file)`. 
        # If I run it as is, it might decode with utf-8 and fail if latin1.
        # But let's try to be slightly helpful to the script runner and allow it to run 
        # IF the parameters were correct in the app (maybe the app expects a clean CSV).
        # However, the user wants to see "App Results". If the App fails, result is Failure.
        
        df_ledger = pd.read_csv(DIARIO_PATH)
        
        # App logic continuing
        if 'amount' in df_ledger.columns:
            df_ledger['amount'] = pd.to_numeric(df_ledger['amount'], errors='coerce').fillna(0.0)
        
        if 'date' in df_ledger.columns:
             df_ledger['date'] = pd.to_datetime(df_ledger['date'])
             
    except Exception as e:
        print(f"CRITICAL ERROR in Ledger Parsing (App Logic): {e}")
        # To allow comparison, I will patch it here LOCALLY to allow the flow to verify Reconciler logic
        # But I note the failure.
        print("--- PATCHING LEDGER PARSING FOR COMPARISON ---")
        try:
             # Use the logic we found works in ad_hoc
             df_ledger = pd.read_csv(DIARIO_PATH, sep=';', encoding='latin1', skiprows=4, header=None, on_bad_lines='warn', engine='python')
             mapping = {2: 'date', 11: 'amount', 15: 'description'} # Map to app expected columns
             df_ledger.rename(columns=mapping, inplace=True)
             
             # Clean amount
             df_ledger['amount'] = df_ledger['amount'].astype(str).str.replace(' ', '')
             if df_ledger['amount'].str.contains(',', regex=False).any():
                  df_ledger['amount'] = df_ledger['amount'].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
             df_ledger['amount'] = pd.to_numeric(df_ledger['amount'], errors='coerce')
             
             # Clean date
             df_ledger['date'] = pd.to_datetime(df_ledger['date'], dayfirst=True, errors='coerce')
             
             # Add source
             df_ledger['source'] = 'Diario'
             
             print(f"Patched Ledger Loaded: {len(df_ledger)} rows")
        except Exception as e2:
             print(f"Patch failed: {e2}")
             return

    # 2. Parse Bank (Mimicking conciliator_app.py)
    print(f"Loading Bank Statements from: {EXTRATOS_DIR}")
    files = glob.glob(os.path.join(EXTRATOS_DIR, "*.pdf"))
    all_bank_dfs = []
    
    for f in files:
        try:
            parser = ParserFacade.get_parser(f)
            if parser:
                print(f"  Parsing {os.path.basename(f)} with {parser.__class__.__name__}")
                df, _ = parser.parse(f)
                df['source_file'] = os.path.basename(f)
                all_bank_dfs.append(df)
            else:
                print(f"  No parser for {os.path.basename(f)}")
        except Exception as e:
            print(f"  Error parsing {os.path.basename(f)}: {e}")
            
    if all_bank_dfs:
        df_bank = TransactionConsolidator.consolidate(all_bank_dfs)
        df_bank['date'] = pd.to_datetime(df_bank['date'])
        
        # Filter Zeros
        df_bank = df_bank[abs(df_bank['amount']) > 0.009].copy()
        
        # Filter Period
        if not df_ledger.empty:
            start_date = df_ledger['date'].min()
            end_date = df_ledger['date'].max()
            df_bank = df_bank[(df_bank['date'] >= start_date) & (df_bank['date'] <= end_date)].copy()
            
        print(f"Bank Data Loaded: {len(df_bank)} rows")
    else:
        print("No Bank Data")
        return

    # 3. Reconcile
    print("Reconciling...")
    reconciler = Reconciler()
    # App logic uses date_tolerance=3
    matched_l, matched_b, unmatched_l, unmatched_b = reconciler.reconcile(df_ledger, df_bank, date_tolerance=TOLERANCE_DAYS)
    
    print(f"Phase 1 Matches (1-to-1): {len(matched_l)} Ledger items")
    
    # 4. Combinatorial
    matcher = CombinatorialMatcher()
    comb_matches, remaining_l, remaining_b = matcher.find_matches(unmatched_l, unmatched_b, tolerance_days=TOLERANCE_DAYS)
    
    print(f"Phase 2 Matches (Comb): {len(comb_matches)} sets found")
    
    # Total Matches
    total_matched_ledger = len(matched_l) + len(remaining_l[remaining_l['matched']==True]) # Wait, remaining_l returned by find_matches is UNMATCHED?
    # Check matcher.py: returns matches list, remaining_ledger, remaining_bank.
    # The 'remaining_ledger' returned is the UNMATCHED portion.
    
    # Total Unmatched
    print(f"Final Unmatched Ledger: {len(remaining_l)}")
    print(f"Final Unmatched Bank: {len(remaining_b)}")
    
    remaining_b.to_csv('divergences_app_not_in_ledger.csv', index=False)
    remaining_l.to_csv('divergences_app_not_in_bank.csv', index=False)

if __name__ == "__main__":
    run_app_logic()
