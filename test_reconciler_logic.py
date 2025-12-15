import pandas as pd
from datetime import date, timedelta
from src.core.reconciler import Reconciler

def test_reconciler():
    print("Testing Reconciler Logic...")
    
    # Mock Ledger (float)
    ledger_data = [
        {'date': date(2025, 1, 1), 'amount': 100.0, 'description': 'Exact Match'},
        {'date': date(2025, 1, 10), 'amount': 200.5, 'description': 'Date Tolerance'},
        {'date': date(2025, 1, 20), 'amount': 300.0, 'description': 'Unmatched'},
    ]
    df_ledger = pd.DataFrame(ledger_data)
    
    # Mock Bank (float, similar values)
    bank_data = [
        {'date': date(2025, 1, 1), 'amount': 100.0, 'description': 'Bank Exact'}, # Exact
        {'date': date(2025, 1, 12), 'amount': 200.5, 'description': 'Bank Late'}, # +2 days
        {'date': date(2025, 1, 25), 'amount': 500.0, 'description': 'Bank Unmatched'},
    ]
    df_bank = pd.DataFrame(bank_data)
    
    reconciler = Reconciler()
    matched_l, matched_b, unmatched_l, unmatched_b = reconciler.reconcile(df_ledger, df_bank)
    
    print(f"Matched Ledger: {len(matched_l)} (Expected 2)")
    print(f"Matched Bank: {len(matched_b)} (Expected 2)")
    print(f"Unmatched Ledger: {len(unmatched_l)} (Expected 1)")
    
    # Verify matches
    matches = matched_l['description'].tolist()
    print(f"Matched Descriptions: {matches}")
    
    if len(matched_l) == 2:
        print("✅ SUCCESS: Tolerance logic working.")
    else:
        print("❌ FAILURE: Tolerance logic failed.")

if __name__ == "__main__":
    test_reconciler()
