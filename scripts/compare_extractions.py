
import pandas as pd
import sys
import os

# Paths
ADHOC_BANK_CSVs = "divergences_not_in_ledger.csv" # Wait, this is UNMATCHED. I need the raw data.
# Ad-hoc script didn't save raw data, only results. 
# I should update ad-hoc or just reuse logic here.

# Let's verify by loading the 'divergences_not_in_ledger.csv' which has unmatched bank items. 
# But I need to see if the missing 27 items were matched or just not there.

# Cleaner: re-run parsing from both scripts and save to CSVs?
# I'll create `scripts/compare_extractions.py`.

from scripts.ad_hoc_reconcile import parse_bank_statements
from src.parsing.facade import ParserFacade
import glob

EXTRATOS_DIR = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extratos"

def compare():
    print("Parsing Ad-Hoc...")
    df_adhoc = parse_bank_statements(EXTRATOS_DIR)
    
    print("Parsing App (Facade)...")
    files = glob.glob(os.path.join(EXTRATOS_DIR, "*.pdf"))
    all_dfs = []
    for f in files:
        parser = ParserFacade.get_parser(f)
        if parser:
            df, _ = parser.parse(f)
            # Ensure dates are datetime
            df['date'] = pd.to_datetime(df['date'])
            # Ensure amounts are float
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
            # Filter zeros like app
            df = df[abs(df['amount']) > 0.009]
            all_dfs.append(df)
            
    df_app = pd.concat(all_dfs) if all_dfs else pd.DataFrame()
    
    # Compare
    print(f"Ad-Hoc: {len(df_adhoc)}")
    print(f"App: {len(df_app)}")
    
    # Find diffs
    # Round amounts to avoid float issues
    df_adhoc['amount_r'] = df_adhoc['Value'].round(2)
    df_app['amount_r'] = df_app['amount'].round(2)
    
    # Store sets of (Date, Amount)
    adhoc_set = set(zip(pd.to_datetime(df_adhoc['Date'], dayfirst=True), df_adhoc['amount_r']))
    app_set = set(zip(df_app['date'], df_app['amount_r']))
    
    only_in_adhoc = adhoc_set - app_set
    only_in_app = app_set - adhoc_set
    
    print(f"Only in Ad-Hoc: {len(only_in_adhoc)}")
    print("Sample Only in Ad-Hoc:")
    for i, x in enumerate(list(only_in_adhoc)[:10]):
        print(x)
        
    print(f"Only in App: {len(only_in_app)}")
    
if __name__ == "__main__":
    compare()
