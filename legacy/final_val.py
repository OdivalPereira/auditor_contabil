
import os
from src.parsing.config.registry import LayoutRegistry
from src.parsing.pipeline import ExtractorPipeline
import pandas as pd

ROOT = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil"
registry = LayoutRegistry(os.path.join(ROOT, "src/parsing/layouts"))
pipeline = ExtractorPipeline(registry)

files = [
    ("BB", "Extrato BB 01 2025.pdf"),
    ("Santander", "Extrato Santander.pdf"),
    ("Sicredi", "Extrato Sicredi  Janeiro 2025.pdf"),
    ("CEF", "Extrato CEF.pdf"),
]

print(f"{'BANK':<12} | {'FILE':<30} | {'TXNS':<5} | {'DUPES':<5} | {'RECON':<5} | {'START':>10} | {'END':>10} | {'SUM':>10} | {'DIFF':>10}")
print("-" * 120)

for bank, fname in files:
    if bank == "BB":
        path = os.path.join(ROOT, f"extratos/01 2025/{fname}")
    elif bank == "Santander" or bank == "CEF":
        path = os.path.join(ROOT, f"extração_pdfs/pdf_modelos/{fname}")
    else:
        path = os.path.join(ROOT, f"extração_pdfs/pdf_modelos/{fname}")
        
    res = pipeline.process_file(path)
    txns = res['transactions']
    df = pd.DataFrame([t.to_dict() for t in txns])
    
    start = res['balance_info'].get('start') or 0.0
    end = res['balance_info'].get('end') or 0.0
    total_sum = df['amount'].sum() if not df.empty else 0.0
    
    expected_end = start + total_sum
    diff = end - expected_end
    reconciled = "YES" if abs(diff) < 0.01 else "NO"
    dupes = len(df[df.duplicated()]) # Should be 0 after parser fix
    
    print(f"{bank:<12} | {fname:<30} | {len(df):<5} | {dupes:<5} | {reconciled:<5} | {start:>10.2f} | {end:>10.2f} | {total_sum:>10.2f} | {diff:>10.2f}")
