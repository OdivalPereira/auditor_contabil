from src.parsing.banks.stone import StonePDFParser

p = StonePDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
df, m = p.parse(f)

print("=" * 80)
print("Day-by-day Stone reconciliation (without tarifas)")
print("=" * 80)
print(f"Starting balance: {m['balance_start']:.2f}")
print(f"Ending balance: {m['balance_end']:.2f}")
print(f"Expected delta: {m['balance_end'] - m['balance_start']:.2f}\n")

# Track running balance
running_bal = m['balance_start']
error_found = False

# Group by date
for date in sorted(df.date.unique()):
    day_txns = df[df.date == date]
    day_sum = day_txns.amount.sum()
    expected_end = running_bal + day_sum
    
    print(f"\n{date} ({len(day_txns)} txns):")
    print(f"  Start: {running_bal:.2f}")
    print(f"  Day sum: {day_sum:.2f}")
    print(f"  Calculated end: {expected_end:.2f}")
    
    # Show first few transactions of each day
    for idx, row in day_txns.head(3).iterrows():
        print(f"    {row['amount']:>10.2f} | {row['description'][:50]}")
    
    if len(day_txns) > 3:
        print(f"    ... ({len(day_txns) - 3} more)")
    
    running_bal = expected_end
    
    # Stop after first 5 days to check
    if date.day > 5:
        print("\n[Stopping after first 5 days for review]")
        break

print("\n" + "=" * 80)
print(f"Running balance after checked days: {running_bal:.2f}")
print(f"Total transactions checked: {len(df[df.date.apply(lambda x: x.day <= 5)])}")
