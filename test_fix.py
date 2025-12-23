import sys
# Clear module cache to force reload
if 'src.parsing.banks.stone' in sys.modules:
    del sys.modules['src.parsing.banks.stone']
if 'src.parsing.base' in sys.modules:
    del sys.modules['src.parsing.base']

from src.parsing.banks.stone import StonePDFParser

parser = StonePDFParser()
df, _ = parser.parse('extratos/Extrato Stones 03 2025.pdf')

pix_maq = df[df['description'].str.contains('Pix.*Maquininha', case=False, na=False, regex=True)]
print(f'Total Pix|Maquininha: {len(pix_maq)}')
print(f'Total transactions: {len(df)}')

wanda = df[df['description'].str.contains('WANDA', case=False, na=False)]
print(f'\nWANDA entries: {len(wanda)}')
if len(wanda) > 0:
    print(wanda[['date', 'description', 'amount']].to_string())

flexcar = df[df['description'].str.contains('FLEXCAR', case=False, na=False)]
print(f'\nFLEXCAR entries: {len(flexcar)}')
if len(flexcar) > 0:
    print(flexcar[['date', 'description', 'amount']].to_string())

print("\nSample composite descriptions (showing if multi-line worked):")
sample = df[df['description'].str.contains('Pix.*Maquininha', case=False, na=False, regex=True)].head(5)
for idx, row in sample.iterrows():
    print(f"{row['date']} | {row['description'][:70]} | R$ {row['amount']:.2f}")
