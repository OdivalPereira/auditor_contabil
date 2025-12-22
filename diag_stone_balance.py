import pdfplumber
from src.parsing.banks.stone import StonePDFParser
import re

f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
pdf = pdfplumber.open(f)

# Test raw extraction WITHOUT the parse() wrapper
p = StonePDFParser()
page1 = pdf.pages[0]
rows, b_start, b_end = p.extract_page(page1)

print("=" * 80)
print("RAW extraction from first page (before parse reversal):")
print(f"First balance (b_start): {b_start}")
print(f"Last balance (b_end): {b_end}")
print(f"Transactions on page 1: {len(rows)}")
if rows:
    print(f"\nFirst tx: {rows[0]}")
    print(f"Last tx: {rows[-1]}")

# Now test WITH parse
df, m = p.parse(f)
print("\n" + "=" * 80)
print("AFTER parse() wrapper (with reversal):")
print(f"Metadata balance_start: {m['balance_start']}")
print(f"Metadata balance_end: {m['balance_end']}")
print(f"Total transactions: {len(df)}")
print(f"Sum: {df.amount.sum():.2f}")
print(f"\nFirst tx in df: date={df.iloc[0]['date']}, amount={df.iloc[0]['amount']:.2f}")
print(f"Last tx in df: date={df.iloc[-1]['date']}, amount={df.iloc[-1]['amount']:.2f}")

# Expected calculation
print("\n" + "=" * 80)
print("EXPECTED:")
print(f"balance_start (01/05) should be LOWEST value (start of month)")
print(f"balance_end (31/05) should be 2313.21")
print(f"Delta: balance_end - balance_start = {m['balance_end'] - m['balance_start']:.2f}")
print(f"Actual sum: {df.amount.sum():.2f}")
print(f"PROBLEM: Sum should equal Delta, but difference is {df.amount.sum() - (m['balance_end'] - m['balance_start']):.2f}")
