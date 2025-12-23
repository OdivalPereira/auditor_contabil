from src.utils.csv_helper import _parse_ledger_csv
from src.parsing.banks.stone import StonePDFParser
import pandas as pd
import os

# Load ledger
ledger_df, company = _parse_ledger_csv("diarios/CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv")

print(f"{'='*70}")
print(f"LEDGER ANALYSIS")
print(f"{'='*70}")
print(f"Total ledger entries: {len(ledger_df)}")
print(f"Company: {company}")
print(f"Date range: {ledger_df['date'].min()} to {ledger_df['date'].max()}")

# Filter Stone entries from ledger
stone_ledger = ledger_df[ledger_df['description'].str.contains('Stone', case=False, na=False)]
print(f"\nTotal Stone entries in ledger: {len(stone_ledger)}")

# Break down by month
for month in [1, 2, 3]:
    start_date = pd.to_datetime(f'2025-{month:02d}-01')
    end_date = pd.to_datetime(f'2025-{month+1:02d}-01') if month < 3 else pd.to_datetime('2025-04-01')
    
    month_stone = stone_ledger[
        (stone_ledger['date'] >= start_date) & (stone_ledger['date'] < end_date)
    ]
    month_name = ['Jan', 'Feb', 'Mar'][month-1]
    print(f"  {month_name} 2025: {len(month_stone)} transactions")

# Parse all Stone PDFs
print(f"\n{'='*70}")
print(f"STONE PDF EXTRACTION")
print(f"{'='*70}")

parser = StonePDFParser()
all_stone_dfs = []
pdf_files = []

# Find all Stone PDFs
extrato_dir = "extratos"
for file in os.listdir(extrato_dir):
    if 'stone' in file.lower() and file.endswith('.pdf'):
        pdf_files.append(file)

pdf_files.sort()  # Sort to process in order

total_extracted = 0
total_tarifas = 0

for pdf_file in pdf_files:
    pdf_path = os.path.join(extrato_dir, pdf_file)
    print(f"\nProcessing: {pdf_file}")
    
    try:
        df, meta = parser.parse(pdf_path)
        tarifas = df[df['description'].str.contains('Tarifa', case=False, na=False)]
        
        print(f"  Extracted: {len(df)} transactions")
        print(f"  Tariffs remaining: {len(tarifas)}")
        
        if 'date' in df.columns and not df.empty:
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        
        all_stone_dfs.append(df)
        total_extracted += len(df)
        total_tarifas += len(tarifas)
    except Exception as e:
        print(f"  ERROR: {e}")

# Combine all PDFs
if all_stone_dfs:
    combined_df = pd.concat(all_stone_dfs, ignore_index=True)
    
    print(f"\n{'='*70}")
    print(f"VALIDATION SUMMARY")
    print(f"{'='*70}")
    print(f"Ledger Stone entries (Q1 2025):  {len(stone_ledger)}")
    print(f"PDF extracted (Q1 2025):          {len(combined_df)}")
    print(f"Difference:                       {len(combined_df) - len(stone_ledger)}")
    print(f"\nTariffs still in extraction:      {total_tarifas}")
    
    if total_tarifas == 0:
        print(f"\n✅ SUCCESS: All non-movement tariffs filtered!")
    elif total_tarifas < 50:
        print(f"\n⚠️  Note: {total_tarifas} tariffs remain (likely balance-changing)")
    else:
        print(f"\n❌ WARNING: Too many tariffs remaining!")
    
    # Check if extraction is close to ledger
    diff_pct = abs(len(combined_df) - len(stone_ledger)) / len(stone_ledger) * 100
    if diff_pct < 5:
        print(f"\n✅ EXCELLENT: Extraction matches ledger within {diff_pct:.1f}%")
    elif diff_pct < 15:
        print(f"\n✓ GOOD: Extraction close to ledger (difference: {diff_pct:.1f}%)")
    else:
        print(f"\n⚠️  Extraction differs from ledger by {diff_pct:.1f}%")
    
    print(f"{'='*70}")
else:
    print("ERROR: No Stone PDFs could be processed!")
