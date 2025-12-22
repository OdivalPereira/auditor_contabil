from src.parsing.banks.sicoob import SicoobPDFParser
import pandas as pd

p = SicoobPDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
df, m = p.parse(f)

print(f"Total Transactions: {len(df)}")
print(f"Total Sum: {df.amount.sum():.2f}")
print(f"Expected Delta: {201651.64 - 20883.58:.2f}")

curr_bal = 20883.58
for i, row in df.iterrows():
    curr_bal += row.amount
    if row.bal_row is not None:
        if abs(curr_bal - row.bal_row) > 0.01:
            print(f"Error at index {i} ({row.date}): Calc {curr_bal:.2f} vs Row {row.bal_row:.2f} | Diff: {curr_bal - row.bal_row:.2f} | Desc: {row.description[:50]}")
            # Reset balance to match the statement to keep tracking errors
            curr_bal = row.bal_row
