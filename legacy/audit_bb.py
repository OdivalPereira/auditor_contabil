
import os
import sys
import pandas as pd

ROOT = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil"
sys.path.append(ROOT)
from src.parsing.pipeline import ExtractorPipeline
from src.parsing.config.registry import LayoutRegistry

registry = LayoutRegistry(os.path.join(ROOT, "src/parsing/layouts"))
pipeline = ExtractorPipeline(registry)

path = os.path.join(ROOT, "extratos/01 2025/Extrato BB 01 2025.pdf")
result = pipeline.process_file(path)
txns = result['transactions']

df = pd.DataFrame([t.to_dict() for t in txns])
print(f"Total Transactions: {len(df)}")
print(f"Grand Total Sum: {df['amount'].sum():.2f}")
print(f"Credits: {df[df['amount'] > 0]['amount'].sum():.2f}")
print(f"Debits: {df[df['amount'] < 0]['amount'].sum():.2f}")
