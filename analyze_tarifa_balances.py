import sys
import os
os.environ['PYTHONWARNINGS'] = 'ignore'

keys_to_remove = [k for k in sys.modules if 'src.parsing' in k]
for k in keys_to_remove:
    del sys.modules[k]

from src.parsing.banks.stone import StonePDFParser

parser = StonePDFParser()

# We need to manually call parse_pdf to get the raw dataframe with balance before it's dropped
df, meta = parser.parse_pdf('extratos/Extrato Stones 03 2025.pdf')

print("="*80)
print("ANALYZING BALANCE CHANGES FOR 'TARIFA' ENTRIES")
print("="*80)

if not df.empty and 'balance' in df.columns:
    count_filtered = 0
    count_kept = 0
    
    for i in range(len(df) - 1):
        row = df.iloc[i]
        desc_lower = str(row['description']).lower()
        
        if 'tarifa' in desc_lower:
            current_balance = row['balance']
            next_row = df.iloc[i + 1]
            prev_balance = next_row['balance']
            
            diff = abs(current_balance - prev_balance)
            will_filter = diff < 0.001
            
            if will_filter:
                count_filtered += 1
            else:
                count_kept += 1
                
            if count_kept < 10 or not will_filter:
                status = "FILTERED" if will_filter else "KEPT"
                print(f"[{status}] {row['description'][:40]:<40} | Bal: {current_balance:10.2f} | Prev Bal: {prev_balance:10.2f} | Diff: {diff:10.4f}")

    print("\n" + "="*80)
    print(f"Summary for 'tarifa':")
    print(f"Total entries with 'tarifa': {count_filtered + count_kept}")
    print(f"Would be filtered: {count_filtered}")
    print(f"Would be kept:     {count_kept}")
    print("="*80)
else:
    print("No balance column found.")
