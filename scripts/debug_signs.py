
import sys
import os
import pandas as pd

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

DIARIO_PATH = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\diarios\CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv"

def debug_signs():
    print(f"Reading {DIARIO_PATH}...")
    try:
        # Raw read to inspect indices
        df = pd.read_csv(
            DIARIO_PATH, 
            sep=';', 
            encoding='latin1', 
            skiprows=4, 
            header=None, 
            on_bad_lines='warn', 
            engine='python'
        )
        print(f"Loaded {len(df)} rows.")
        
        # Check Account Columns (3 and 7)
        # 3 = Debit, 7 = Credit
        print("\n--- Column Analysis ---")
        col3 = df[3].astype(str)
        col7 = df[7].astype(str)
        
        print("Column 3 (Debit) Top 5 Values:")
        print(col3.value_counts().head(5))
        
        print("\nColumn 7 (Credit) Top 5 Values:")
        print(col7.value_counts().head(5))
        
        # Combine to find Bank Account
        all_accs = pd.concat([col3, col7])
        mode_acc = all_accs.mode()[0]
        print(f"\nInferred Bank Account ID (Mode): '{mode_acc}'")
        
        # Count occurrences
        in_debit = (col3 == mode_acc).sum()
        in_credit = (col7 == mode_acc).sum()
        print(f"Occurrences in Debit (Inflow?): {in_debit}")
        print(f"Occurrences in Credit (Outflow?): {in_credit}")
        
        # Check Sample Rows
        print("\n--- Sample Rows Logic Test ---")
        # Find 5 rows where Bank is in Credit (Outflow)
        neg_samples = df[df[7].astype(str) == mode_acc].head(5)
        print("Expected NEGATIVE (Bank in Credit):")
        # Cols 2 (Date), 11 (Amount), 15 (Desc)
        print(neg_samples[[2, 3, 7, 11, 15]].to_string())
        
        # Find 5 rows where Bank is in Debit (Inflow)
        pos_samples = df[df[3].astype(str) == mode_acc].head(5)
        print("\nExpected POSITIVE (Bank in Debit):")
        print(pos_samples[[2, 3, 7, 11, 15]].to_string())
        
        # Verify Amounts Parsing
        print("\n--- Amount Parsing Verification ---")
        sample_amts = df[11].head(5).astype(str)
        print("Raw Amounts:")
        print(sample_amts)
        # Check cleaning logic
        cleaned = sample_amts.str.replace(' ', '')
        if cleaned.str.contains(',', regex=False).any():
             cleaned = cleaned.str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
        print("Cleaned Floats:")
        print(pd.to_numeric(cleaned, errors='coerce'))

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_signs()
