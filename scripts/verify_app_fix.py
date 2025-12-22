
import sys
import os
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.csv_helper import _parse_ledger_csv

DIARIO_PATH = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\diarios\CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv"

def verify():
    print(f"Testing _parse_ledger_csv with {DIARIO_PATH}")
    try:
        df = _parse_ledger_csv(DIARIO_PATH)
        print(f"Success! Rows: {len(df)}")
        print("Columns:", df.columns.tolist())
        print(df.head())
        
        if len(df) > 0 and 'amount' in df.columns:
            print("Validation Passed.")
            print("\nSample Amounts (Check Signs):")
            print(df[['date', 'description', 'amount']].head(10))
            
            negatives = df[df['amount'] < 0]
            print(f"\nTotal Negatives: {len(negatives)}")
            if not negatives.empty:
                print("Sample Negative:")
                print(negatives[['date', 'description', 'amount']].iloc[0])
        else:
            print("Validation Failed (Empty or missing columns).")
            
    except Exception as e:
        print(f"Validation Error: {e}")

if __name__ == "__main__":
    verify()
