import sys
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser
import pandas as pd

parser = StonePDFParser()
extrato_dir = "extratos"
pdf_files = [f for f in os.listdir(extrato_dir) if 'stone' in f.lower() and f.endswith('.pdf')]
pdf_files.sort()

print("="*80)
print("Q1 2025 STONE EXTRACTION SUMMARY (ALL MONTHS)")
print("="*80)

total_all = 0
for pdf_file in pdf_files:
    pdf_path = os.path.join(extrato_dir, pdf_file)
    try:
        df, _ = parser.parse(pdf_path)
        print(f"{pdf_file:<30} | Transactions: {len(df):>5}")
        total_all += len(df)
    except Exception as e:
        print(f"{pdf_file:<30} | ERROR: {e}")

print("-"*80)
print(f"{'TOTAL Q1 2025':<30} | Transactions: {total_all:>5}")
print("="*80)

print("\nEXPLANATION:")
print("- The previous 4,262 was inflated by multi-line descriptions being split into separate rows.")
print("- The 1,269 I cited was for MARCH alone.")
print("- Now calculating the true sum of all 3 months with correct grouping and 0 tariffs.")
