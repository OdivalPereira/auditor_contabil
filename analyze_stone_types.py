from src.parsing.banks.stone import StonePDFParser

p = StonePDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
df, m = p.parse(f)

# Analyze by type
entradas = df[df.description.str.contains('Entrada', na=False, case=False)]
saidas = df[df.description.str.contains('Saída|Saida', na=False, case=False, regex=True)]
other = df[~df.description.str.contains('Entrada|Saída|Saida', na=False, case=False, regex=True)]

print("Transaction breakdown:")
print(f"Entradas: {len(entradas)} txns, sum: {entradas.amount.sum():.2f}")
print(f"  Positive: {len(entradas[entradas.amount > 0])}, Negative: {len(entradas[entradas.amount < 0])}")
print(f"\nSaídas: {len(saidas)} txns, sum: {saidas.amount.sum():.2f}")
print(f"  Positive: {len(saidas[saidas.amount > 0])}, Negative: {len(saidas[saidas.amount < 0])}")
print(f"\nOther: {len(other)} txns, sum: {other.amount.sum():.2f}")

print(f"\nExpected delta: {m['balance_end'] - m['balance_start']:.2f}")
print(f"Actual sum: {df.amount.sum():.2f}")
print(f"\nSample Entradas:")
print(entradas.head(5)[['date', 'amount', 'description']].to_string())
print(f"\nSample Saídas:")
print(saidas.head(5)[['date', 'amount', 'description']].to_string())
