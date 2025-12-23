import pandas as pd
from src.parsing.banks.stone import StonePDFParser
import os

# 1. Ledger Counts
l_df = pd.read_csv('diarios/CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv', sep=';', encoding='latin-1', skiprows=2)
l_df['Data'] = pd.to_datetime(l_df['Data'], format='%d/%m/%Y').dt.date
l_df['Valor'] = l_df['Valor'].astype(float)

targets = [
    ('2025-02-07', 31.50, "Luana 07/02"),
    ('2025-03-03', 43.65, "Antecipação 03/03"),
    ('2025-03-25', 21.72, "Antecipação 25/03"),
]

print("--- LEDGER COUNTS ---")
for ds, amt, label in targets:
    dt = pd.to_datetime(ds).date()
    count = l_df[(l_df['Data'] == dt) & (abs(l_df['Valor'] - amt) < 0.01)].shape[0]
    print(f"{label}: {count}")

# 2. Bank Counts
parser = StonePDFParser()
print("\n--- BANK COUNTS ---")
pdfs = ['extratos/Extrato Stones 02 2025.pdf', 'extratos/Extrato Stones 03 2025.pdf']
all_bank_txns = []
for p in pdfs:
    df, _ = parser.parse(p)
    all_bank_txns.append(df)

b_df = pd.concat(all_bank_txns)
b_df['date'] = pd.to_datetime(b_df['date']).dt.date

for ds, amt, label in targets:
    dt = pd.to_datetime(ds).date()
    count = b_df[(b_df['date'] == dt) & (abs(b_df['amount'] - amt) < 0.01)].shape[0]
    print(f"{label}: {count}")
    
    # Also print descriptions found in bank for these amounts/dates
    matches = b_df[(b_df['date'] == dt) & (abs(b_df['amount'] - amt) < 0.01)]
    if not matches.empty:
        print("  Bank Descriptions:")
        for idx, row in matches.iterrows():
            print(f"    - {row['description']} ({row['amount']})")
