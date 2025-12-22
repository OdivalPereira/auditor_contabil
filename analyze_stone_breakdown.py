from src.parsing.banks.stone import StonePDFParser

p = StonePDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
df, m = p.parse(f)

# Categorize transactions
entradas = df[df.amount > 0]
saidas = df[df.amount < 0]

print("STONE TRANSACTION BREAKDOWN:")
print(f"Entradas (+): {len(entradas)} txns, sum: {entradas.amount.sum():.2f}")
print(f"Saídas (-): {len(saidas)} txns, sum: {saidas.amount.sum():.2f}")
print(f"Total: {df.amount.sum():.2f}")

print(f"\nExpected: {m['balance_end'] - m['balance_start']:.2f}")
print(f"For reconciliation, need: Entradas - Saídas = +222.76")
print(f"Actual: {entradas.amount.sum()} + {saidas.amount.sum()} = {df.amount.sum():.2f}")

print("\n\nSample ENTRADAS:")
print(entradas.head(10)[['date', 'amount', 'description']].to_string())

print("\n\nSample SAÍDAS:")
print(saidas.head(10)[['date', 'amount', 'description']].to_string())

print("\nLargest SAÍDAS:")
print(saidas.sort_values('amount').head(10)[['date', 'amount', 'description']].to_string())
