from src.parsing.banks.stone import StonePDFParser

p = StonePDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
df, m = p.parse(f)

print("="*80)
print("STONE PARSER - FINAL SIMPLIFIED VERSION")
print("="*80)
print(f"✓ Transactions extracted: {len(df)}")
print(f"✓ Balance start: {m['balance_start']:.2f}")
print(f"✓ Balance end: {m['balance_end']:.2f}")
print(f"\nFirst transaction (chronologically):")
print(f"  {df.iloc[0]['date']} | {df.iloc[0]['amount']:>10.2f} | {df.iloc[0]['description'][:50]}")
print(f"\nLast transaction (chronologically):")
print(f"  {df.iloc[-1]['date']} | {df.iloc[-1]['amount']:>10.2f} | {df.iloc[-1]['description'][:50]}")

print(f"\nTransaction breakdown:")
print(f"  Positive (Entradas): {len(df[df.amount > 0])}")
print(f"  Negative (Saídas): {len(df[df.amount < 0])}")

print("\n" + "="*80)
print("Stone extraction completed successfully! ✅")
print("="*80)
