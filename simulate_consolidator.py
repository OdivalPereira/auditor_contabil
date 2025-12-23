import pandas as pd
from src.parsing.banks.stone import StonePDFParser
from src.core.consolidator import TransactionConsolidator

parser = StonePDFParser()
pdfs = ['extratos/Extrato Stones 02 2025.pdf', 'extratos/Extrato Stones 03 2025.pdf']
dfs = []
for p in pdfs:
    df, _ = parser.parse(p)
    df['source_file'] = p # Add source_file like scan.py does
    dfs.append(df)

consolidated = TransactionConsolidator.consolidate(dfs)

print(f"Final Consolidated Count: {len(consolidated)}")
print("\n--- TARGET COUNTS IN CONSOLIDATED ---")

targets = [
    ('2025-02-07', 31.50, "Luana 07/02"),
    ('2025-03-03', 43.65, "Antecipação 03/03"),
    ('2025-03-25', 21.72, "Antecipação 25/03"),
]

for ds, amt, label in targets:
    dt = pd.to_datetime(ds).date()
    count = consolidated[(consolidated['date'] == dt) & (abs(consolidated['amount'] - amt) < 0.01)].shape[0]
    print(f"{label}: {count}")
