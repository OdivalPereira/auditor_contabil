from src.parsing.banks.stone import StonePDFParser

p = StonePDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
df, m = p.parse(f)

# Separate tarifas from other transactions
tarifas = df[df.description.str.contains('Tarifa', na=False, case=False)]
non_tarifas = df[~df.description.str.contains('Tarifa', na=False, case=False)]

print(f"Total transactions: {len(df)}")
print(f"Tarifas: {len(tarifas)} (sum: {tarifas.amount.sum():.2f})")
print(f"Non-tarifas: {len(non_tarifas)} (sum: {non_tarifas.amount.sum():.2f})")
print(f"\nBalance Start: {m['balance_start']:.2f}")
print(f"Balance End: {m['balance_end']:.2f}")
print(f"Expected Delta: {m['balance_end'] - m['balance_start']:.2f}")
print(f"\nNon-tarifa sum: {non_tarifas.amount.sum():.2f}")
print(f"Difference (without tarifas): {non_tarifas.amount.sum() - (m['balance_end'] - m['balance_start']):.2f}")
print(f"\nWith tarifas sum: {df.amount.sum():.2f}")
print(f"Difference (with tarifas): {df.amount.sum() - (m['balance_end'] - m['balance_start']):.2f}")
