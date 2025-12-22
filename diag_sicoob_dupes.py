from src.parsing.banks.sicoob import SicoobPDFParser
import pandas as pd

p = SicoobPDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
df, m = p.parse(f)

print(f"Total Transactions: {len(df)}")

# Find potential duplicates: same Date and same Amount
potential = df[df.duplicated(subset=['date', 'amount'], keep=False)]
print(f"Found {len(potential)} potential duplicate rows.")

dupes_indices = []
for i in range(len(potential)):
    idx1 = potential.index[i]
    row1 = potential.iloc[i]
    for j in range(i + 1, len(potential)):
        idx2 = potential.index[j]
        row2 = potential.iloc[j]
        
        if row1.date == row2.date and row1.amount == row2.amount:
            # Check description overlap
            words1 = set(row1.description.split())
            words2 = set(row2.description.split())
            common = words1.intersection(words2)
            if len(common) > 2 or (len(words1) > 0 and common == words1) or (len(words2) > 0 and common == words2):
                if idx1 not in dupes_indices: dupes_indices.append(idx1)
                if idx2 not in dupes_indices: dupes_indices.append(idx2)

print(f"Fuzzy duplicates count (indices): {len(dupes_indices)}")
if dupes_indices:
    sample = df.loc[dupes_indices].sort_values(['date', 'amount']).head(20)
    print(sample.to_string())
