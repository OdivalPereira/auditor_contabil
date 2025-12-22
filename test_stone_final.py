from src.parsing.banks.stone import StonePDFParser

p = StonePDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
df, m = p.parse(f)

delta = m['balance_end'] - m['balance_start']

print("=" * 80)
print("STONE RECONCILIATION TEST (Final)")
print("=" * 80)
print(f"Transactions: {len(df)} (tarifas excluídas)")
print(f"Balance start: {m['balance_start']:.2f}")
print(f"Balance end: {m['balance_end']:.2f}")
print(f"Expected delta: {delta:.2f}")
print(f"Actual sum: {df.amount.sum():.2f}")
print(f"Difference: {abs(df.amount.sum() - delta):.2f}")
print(f"\n✅ MATCH: {abs(df.amount.sum() - delta) < 1.0}")

print("\nFirst 5 transactions:")
print(df.head(5)[['date', 'amount', 'description']].to_string())

print("\nLast 5 transactions:")
print(df.tail(5)[['date', 'amount', 'description']].to_string())
