from src.parsing.banks.stone import StonePDFParser
from datetime import datetime

p = StonePDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf'
df, m = p.parse(f)

d = datetime(2025, 5, 1).date()
day1 = df[df.date == d]

print('Transações do dia 01/05/2025:')
print(day1[['date', 'amount', 'description']].to_string())
print(f'\nBalance start no metadata: {m["balance_start"]:.2f}')
print(f'Após -2090: {m["balance_start"] - 2090:.2f}')
print(f'\nPROBLEMA: O saldo inicial de {m["balance_start"]:.2f} parece MUITO BAIXO')
print(f'Se a primeira transação é -2090, chegaria a {m["balance_start"] - 2090:.2f}')
print(f'\nVamos checar se balance_start/end estão corretos:')
print(f'balance_start (deveria ser início do mês 01/05): {m["balance_start"]:.2f}')
print(f'balance_end (deveria ser fim do mês 31/05): {m["balance_end"]:.2f}')
