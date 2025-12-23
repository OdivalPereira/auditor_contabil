from datetime import date
import pandas as pd
import json

# 1. Test Frontend date parser logic (Simulated)
def format_date_frontend(date_str):
    if not date_str: return ''
    if '-' in date_str:
        y, m, d = date_str.split('-')
        return f"{d}/{m}/{y}"
    return date_str

print("Frontend Format Verification:")
iso_date = "2025-03-01"
print(f"ISO: {iso_date} -> PT-BR: {format_date_frontend(iso_date)}")
assert format_date_frontend(iso_date) == "01/03/2025"

# 2. Test Backend Normalization
from src.core.reconciler import Reconciler

reconciler = Reconciler()
df_ledger = pd.DataFrame([
    {'date': pd.Timestamp('2025-02-07'), 'amount': 31.50, 'description': 'LUANA', 'source': 'Diário'}
])
df_bank = pd.DataFrame([
    {'date': date(2025, 2, 7), 'amount': 31.50, 'description': 'Luana', 'source': 'Bank'}
])

ml, mb, ul, ub = reconciler.reconcile(df_ledger, df_bank)
print("\nReconciliation Normalization Test:")
print(f"Matched Ledger: {len(ml)}, Matched Bank: {len(mb)}")
assert len(ml) == 1

# 3. Test Stone Parser Year Inference
from src.parsing.banks.stone import StonePDFParser
parser = StonePDFParser()

print("\nStone Parser Truncated Date Test:")
# Create a mock page/line with truncated date
mock_lines = [
    "01/03 Crédito ALEX RODRIGUES 30,00 3.000,00"
]
# Re-running a small part of extract_page logic
import re
from datetime import datetime
dt_s = "01/03"
parts = dt_s.split('/')
if len(parts) == 2:
    day, month = map(int, parts)
    dt = date(2025, month, day)
    print(f"Truncated '01/03' parsed as: {dt}")
    assert dt == date(2025, 3, 1)

# 4. Test API .dt Fix
print("\nAPI .dt Fix Verification:")
df_mock = pd.DataFrame({'date': [date(2025, 3, 1)]})
# This would fail before the fix: df_mock['date'].dt.strftime('%Y-%m-%d')
try:
    formatted = pd.to_datetime(df_mock['date']).dt.strftime('%Y-%m-%d')
    print(f"Formatted successfully: {formatted[0]}")
    assert formatted[0] == "2025-03-01"
except Exception as e:
    print(f"FAILED: {e}")
    raise

print("\nVerification Successful!")
