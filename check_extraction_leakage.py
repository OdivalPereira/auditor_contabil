from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator
import pandas as pd
import os

facade = ParserFacade()
print("--- BANK EXTRACTION CHECK (FACADE) ---")
pdfs = ['extratos/Extrato Stones 02 2025.pdf', 'extratos/Extrato Stones 03 2025.pdf']

total_raw_rows = 0
dfs = []

for p in pdfs:
    # Now use the actual parse method which includes deduplication and filtering
    df, _ = facade.parse(p)
    print(f"File {p}: Final DF has {len(df)} transactions. Columns: {df.columns.tolist()}")
    if 'internal_id' in df.columns:
        print(f"  - internal_id is PRESENT")
    else:
        print(f"  - internal_id is MISSING")
    dfs.append(df)

final_df = TransactionConsolidator.consolidate(dfs)
print(f"\nTOTAL CONSOLIDATED BANK TRANSACTIONS (Feb+Mar): {len(final_df)}")
print(f"EXPECTED: 2347 (if 2347 + 55 = 2402)")

targets = [
    ('2025-02-07', 31.50, "Luana 07/02"),
    ('2025-03-25', 21.72, "Antecipação 25/03"),
]

print("\n--- TARGET VERIFICATION ---")
for ds, amt, label in targets:
    dt = pd.to_datetime(ds).date()
    count = final_df[(final_df['date'] == dt) & (abs(final_df['amount'] - amt) < 0.01)].shape[0]
    print(f"{label}: {count}")
