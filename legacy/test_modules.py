import os
import pandas as pd
from src.parsing.sources.ledger_pdf import LedgerParser
from src.parsing.banks.bb import BBMonthlyPDFParser
from src.core.reconciler import Reconciler

# Paths
LEDGER_PATH = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/diarios/Diário Banco do Brasil.pdf"
BANK_DIR = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/extratos"

def test_modules():
    print("Testing Modules...")
    
    # 1. Test Ledger Parser
    print("1. Testing LedgerParser...")
    l_parser = LedgerParser()
    df_ledger = l_parser.parse(LEDGER_PATH)
    print(f"   Ledger Transactions: {len(df_ledger)}")
    assert len(df_ledger) > 0, "Ledger parsing failed"
    
    # 2. Test Bank Parser (BB PDF)
    print("2. Testing BBMonthlyPDFParser...")
    b_parser = BBMonthlyPDFParser()
    bank_txns = []
    
    # Find a PDF to test
    for root, dirs, files in os.walk(BANK_DIR):
        for f in files:
            if f.startswith('ComprovanteBB') and f.endswith('.pdf'):
                path = os.path.join(root, f)
                df = b_parser.parse(path)
                bank_txns.append(df)
                
    df_bank = pd.concat(bank_txns, ignore_index=True)
    print(f"   Bank Transactions: {len(df_bank)}")
    assert len(df_bank) > 0, "Bank parsing failed"
    
    # 3. Test Reconciler
    print("3. Testing Reconciler...")
    
    # Filter Bank
    start_date = df_ledger['date'].min()
    end_date = df_ledger['date'].max()
    df_bank_filtered = df_bank[
        (df_bank['date'] >= start_date) & 
        (df_bank['date'] <= end_date)
    ].copy()
    
    reconciler = Reconciler()
    ml, mb, ul, ub = reconciler.reconcile(df_ledger, df_bank_filtered)
    
    print(f"   Unmatched Ledger: {len(ul)}")
    print(f"   Unmatched Bank: {len(ub)}")
    
    assert len(ul) == 4, f"Expected 4 unmatched ledger, got {len(ul)}"
    assert len(ub) == 19, f"Expected 19 unmatched bank, got {len(ub)}"
    
    print("SUCCESS: All modules verified!")

if __name__ == "__main__":
    test_modules()
