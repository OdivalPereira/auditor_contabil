from src.parsing.banks.stone import StonePDFParser
import pandas as pd

parser = StonePDFParser()
df, _ = parser.parse('extratos/Extrato Stones 03 2025.pdf')

print("="*80)
print("INVESTIGATING POTENTIAL MULTI-LINE DUPLICATION")
print("="*80)

# Show last transactions (March ends at line end, which is start due to reverse order)
print("\nLast 30 transactions (chronologically):")
print(df.tail(30)[['date', 'description', 'amount']].to_string())

# Look for "Pix | Maquininha" pattern
pix_maquininha = df[df['description'].str.contains('Pix.*Maquininha', case=False, na=False, regex=True)]
print(f"\n\nTotal 'Pix | Maquininha' entries: {len(pix_maquininha)}")
print("\nSample 'Pix | Maquininha' entries:")
print(pix_maquininha[['date', 'description', 'amount']].head(20).to_string())

# Look for WANDA
wanda = df[df['description'].str.contains('WANDA', case=False, na=False)]
print(f"\n\nTotal 'WANDA' entries: {len(wanda)}")
if len(wanda) > 0:
    print("\nWANDA entries:")
    print(wanda[['date', 'description', 'amount']].to_string())

# Look for FLEXCAR
flexcar = df[df['description'].str.contains('FLEXCAR', case=False, na=False)]
print(f"\n\nTotal 'FLEXCAR' entries: {len(flexcar)}")
if len(flexcar) > 0:
    print("\nFLEXCAR entries:")
    print(flexcar[['date', 'description', 'amount']].to_string())
