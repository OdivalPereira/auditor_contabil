
import sys
import os
import pandas as pd
import glob

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.csv_helper import _parse_ledger_csv
from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator

DIARIO_PATH = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\diarios\CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv"
EXTRATOS_DIR = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extratos"

def debug():
    print("--- Debugging Duplication ---")
    
    # 1. Ledger
    print(f"Parsing Ledger: {DIARIO_PATH}")
    df_ledger = _parse_ledger_csv(DIARIO_PATH)
    print(f"Ledger Total Rows: {len(df_ledger)}")
    
    # Check for duplicates (Date + Amount + Description)
    dup_l = df_ledger[df_ledger.duplicated(subset=['date', 'amount', 'description'], keep=False)]
    print(f"Ledger Exact Duplicates: {len(dup_l)}")
    if len(dup_l) > 0:
        print(dup_l.sort_values(['date', 'amount']).head(10))
        
    # Check for Value + Date duplicates (User's claim)
    dup_val_date_l = df_ledger[df_ledger.duplicated(subset=['date', 'amount'], keep=False)]
    print(f"Ledger Value+Date Duplicates: {len(dup_val_date_l)}")
    
    # 2. Bank
    print(f"Parsing Bank from {EXTRATOS_DIR}")
    files = glob.glob(os.path.join(EXTRATOS_DIR, "*.pdf"))
    all_dfs = []
    
    for f in files:
        parser = ParserFacade.get_parser(f)
        if parser:
            df, _ = parser.parse(f)
            df['source_file'] = os.path.basename(f)
            all_dfs.append(df)
            
    df_bank = TransactionConsolidator.consolidate(all_dfs)
    df_bank['date'] = pd.to_datetime(df_bank['date'])
    df_bank = df_bank[abs(df_bank['amount']) > 0.009]
    
    print(f"Bank Total Rows: {len(df_bank)}")
    
    # Check Duplicates
    dup_b = df_bank[df_bank.duplicated(subset=['date', 'amount', 'description'], keep=False)]
    print(f"Bank Exact Duplicates: {len(dup_b)}")
    if len(dup_b) > 0:
        print(dup_b.sort_values(['date', 'amount']).head(10))
        
    dup_val_date_b = df_bank[df_bank.duplicated(subset=['date', 'amount'], keep=False)]
    print(f"Bank Value+Date Duplicates: {len(dup_val_date_b)}")
    
    # Analyze specific date from screenshot: 2025-03-31
    print("\n--- Analyze 2025-03-31 ---")
    target_date = pd.Timestamp("2025-03-31")
    
    l_day = df_ledger[df_ledger['date'] == target_date]
    b_day = df_bank[df_bank['date'] == target_date]
    
    print(f"Ledger items on 31/03: {len(l_day)}")
    print(l_day[['amount', 'description']].to_string())
    
    print(f"Bank items on 31/03: {len(b_day)}")
    print(b_day[['amount', 'description', 'source_file']].to_string())

if __name__ == "__main__":
    debug()
