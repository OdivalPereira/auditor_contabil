import sys
import os
import pandas as pd
import glob

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.csv_helper import _parse_ledger_csv
from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator
from src.core.reconciler import Reconciler
from src.core.matcher import CombinatorialMatcher

DIARIO_PATH = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\diarios\CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv"
EXTRATOS_DIR = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\extratos"

def test_full_flow():
    print("="*60)
    print("END-TO-END RECONCILIATION TEST")
    print("="*60)
    
    # 1. Load Ledger
    print("\n[1] Loading Ledger...")
    try:
        df_ledger = _parse_ledger_csv(DIARIO_PATH)
        print(f"✓ Loaded {len(df_ledger)} ledger rows")
        print(f"  Columns: {df_ledger.columns.tolist()}")
        print(f"  Date range: {df_ledger['date'].min()} to {df_ledger['date'].max()}")
        print(f"  Amount range: {df_ledger['amount'].min():.2f} to {df_ledger['amount'].max():.2f}")
        print(f"  Sample (first 3):")
        print(df_ledger[['date', 'amount', 'description']].head(3).to_string())
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return
    
    # 2. Load Bank Statements
    print("\n[2] Loading Bank Statements...")
    try:
        files = glob.glob(os.path.join(EXTRATOS_DIR, "*.pdf"))
        print(f"  Found {len(files)} PDF files")
        
        all_dfs = []
        for f in files:
            parser = ParserFacade.get_parser(f)
            if parser:
                df, _ = parser.parse(f)
                df['source_file'] = os.path.basename(f)
                all_dfs.append(df)
                print(f"  ✓ Parsed {os.path.basename(f)}: {len(df)} transactions")
        
        df_bank = TransactionConsolidator.consolidate(all_dfs)
        df_bank['date'] = pd.to_datetime(df_bank['date'])
        
        # Filter zeros
        df_bank = df_bank[abs(df_bank['amount']) > 0.009]
        
        print(f"✓ Consolidated {len(df_bank)} bank transactions")
        print(f"  Date range: {df_bank['date'].min()} to {df_bank['date'].max()}")
        print(f"  Amount range: {df_bank['amount'].min():.2f} to {df_bank['amount'].max():.2f}")
        print(f"  Sample (first 3):")
        print(df_bank[['date', 'amount', 'description']].head(3).to_string())
        
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. Filter Bank by Ledger Period
    print("\n[3] Filtering Bank by Ledger Period...")
    start_date = df_ledger['date'].min()
    end_date = df_ledger['date'].max()
    df_bank_filtered = df_bank[(df_bank['date'] >= start_date) & (df_bank['date'] <= end_date)].copy()
    print(f"✓ {len(df_bank_filtered)} bank transactions in ledger period")
    
    # 4. Reconcile (Phase 1)
    print("\n[4] Running Reconciliation (Phase 1: Direct Matching)...")
    try:
        reconciler = Reconciler()
        matched_l, matched_b, unmatched_l, unmatched_b = reconciler.reconcile(
            df_ledger, df_bank_filtered, date_tolerance=3
        )
        print(f"✓ Phase 1 Results:")
        print(f"  Matched Ledger: {len(matched_l)}")
        print(f"  Matched Bank: {len(matched_b)}")
        print(f"  Unmatched Ledger: {len(unmatched_l)}")
        print(f"  Unmatched Bank: {len(unmatched_b)}")
        
        if len(matched_l) > 0:
            print(f"\n  Sample Match:")
            print(matched_l[['date', 'amount', 'description']].iloc[0])
            print(matched_b[['date', 'amount', 'description']].iloc[0])
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 5. Combinatorial Matching (Phase 2)
    print("\n[5] Running Combinatorial Matching (Phase 2)...")
    try:
        matcher = CombinatorialMatcher()
        comb_matches, remaining_l, remaining_b = matcher.find_matches(
            unmatched_l, unmatched_b, tolerance_days=3
        )
        print(f"✓ Phase 2 Results:")
        print(f"  Combinatorial Matches: {len(comb_matches)}")
        print(f"  Final Unmatched Ledger: {len(remaining_l)}")
        print(f"  Final Unmatched Bank: {len(remaining_b)}")
    except Exception as e:
        print(f"✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 6. Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    total_ledger = len(df_ledger)
    total_bank = len(df_bank_filtered)
    total_matched_l = len(matched_l) + sum(len(m['ledger_items']) for m in comb_matches)
    total_matched_b = len(matched_b) + len(comb_matches)
    
    print(f"Ledger: {total_matched_l}/{total_ledger} matched ({100*total_matched_l/total_ledger:.1f}%)")
    print(f"Bank: {total_matched_b}/{total_bank} matched ({100*total_matched_b/total_bank:.1f}%)")
    print(f"\nUnmatched Ledger: {len(remaining_l)}")
    print(f"Unmatched Bank: {len(remaining_b)}")
    
    # Save results
    remaining_b.to_csv('test_unmatched_bank.csv', index=False)
    remaining_l.to_csv('test_unmatched_ledger.csv', index=False)
    print(f"\n✓ Results saved to test_unmatched_*.csv")

if __name__ == "__main__":
    test_full_flow()
