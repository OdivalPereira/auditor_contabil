from src.utils.csv_helper import _parse_ledger_csv
from src.parsing.banks.stone import StonePDFParser
import pandas as pd
import os

# Load ledger
ledger_df, company = _parse_ledger_csv("diarios/CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv")
stone_ledger = ledger_df[ledger_df['description'].str.contains('Stone', case=False, na=False)]

# Parse Stone PDFs
parser = StonePDFParser()
pdf_files = ['extratos/Extrato Stones 01 2025.pdf', 
             'extratos/Extrato Stones 02 2025.pdf',
             'extratos/Extrato Stones 03 2025.pdf']

all_dfs = []
for pdf in pdf_files:
    df, _ = parser.parse(pdf)
    all_dfs.append(df)

combined_pdf = pd.concat(all_dfs, ignore_index=True)

print("="*80)
print("DETAILED STONE TRANSACTION ANALYSIS")
print("="*80)

# 1. Check for duplicates
print("\n1. DUPLICATE CHECK")
print("-" * 80)
duplicates = combined_pdf[combined_pdf.duplicated(subset=['date', 'amount', 'description'], keep=False)]
print(f"Duplicate transactions found: {len(duplicates)}")
if len(duplicates) > 0:
    print("\nSample duplicates:")
    print(duplicates[['date', 'description', 'amount']].head(20))

# 2. Analyze transaction types
print("\n2. TRANSACTION TYPE BREAKDOWN")
print("-" * 80)

# Categorize transactions
tarifa_debito = combined_pdf[combined_pdf['description'].str.contains('Débito Tarifa', case=False, na=False)]
tarifa_pix = combined_pdf[combined_pdf['description'].str.contains('Pix.*Maquininha', case=False, na=False, regex=True)]
recebimento = combined_pdf[combined_pdf['description'].str.contains('Recebimento|vendas', case=False, na=False)]
transferencias = combined_pdf[combined_pdf['description'].str.contains('Transfer', case=False, na=False)]
creditos_individuais = combined_pdf[
    (~combined_pdf['description'].str.contains('Tarifa|Maquininha|Recebimento|Transfer', case=False, na=False, regex=True)) &
    (combined_pdf['amount'] > 0)
]
debitos_individuais = combined_pdf[
    (~combined_pdf['description'].str.contains('Tarifa|Maquininha|Recebimento|Transfer', case=False, na=False, regex=True)) &
    (combined_pdf['amount'] < 0)
]

print(f"Débito Tarifa:              {len(tarifa_debito):5} transactions")
print(f"Pix | Maquininha (fees):    {len(tarifa_pix):5} transactions")
print(f"Recebimento vendas:         {len(recebimento):5} transactions")
print(f"Transferências:             {len(transferencias):5} transactions")
print(f"Créditos individuais:       {len(creditos_individuais):5} transactions")
print(f"Débitos individuais:        {len(debitos_individuais):5} transactions")
print(f"{'_'*40}")
print(f"TOTAL:                      {len(combined_pdf):5} transactions")

# 3. Compare individual credits with consolidated ledger receipts
print("\n3. RECONCILIATION ANALYSIS")
print("-" * 80)

# Sum of individual credits (potential sales)
individual_sales = combined_pdf[
    (combined_pdf['amount'] > 0) &
    (~combined_pdf['description'].str.contains('Recebimento|Transfer|Antecipação', case=False, na=False, regex=True))
]

# Sum of "Recebimento vendas" type entries
recebimento_entries = combined_pdf[combined_pdf['description'].str.contains('Recebimento|Antecipação', case=False, na=False)]

print(f"\nIndividual sales (credits):       {len(individual_sales)} transactions, Total: R$ {individual_sales['amount'].sum():,.2f}")
print(f"Recebimento/Antecipação entries:  {len(recebimento_entries)} transactions, Total: R$ {recebimento_entries['amount'].sum():,.2f}")
print(f"\nLedger Stone entries:             {len(stone_ledger)} transactions, Total: R$ {stone_ledger['amount'].sum():,.2f}")

# 4. Show samples
print("\n4. SAMPLE TRANSACTIONS FROM EACH CATEGORY")
print("-" * 80)

print("\n4.1. Sample 'Débito Tarifa' (should be filtered?):")
print(tarifa_debito[['date', 'description', 'amount']].head(5).to_string(index=False))

print("\n4.2. Sample 'Pix | Maquininha' fees:")
if len(tarifa_pix) > 0:
    print(tarifa_pix[['date', 'description', 'amount']].head(5).to_string(index=False))
else:
    print("None found")

print("\n4.3. Sample 'Recebimento vendas':")
if len(recebimento) > 0:
    print(recebimento[['date', 'description', 'amount']].head(5).to_string(index=False))
else:
    print("None found")

print("\n4.4. Sample individual credits (probable sales):")
print(creditos_individuais[['date', 'description', 'amount']].head(10).to_string(index=False))

# 5. Monthly breakdown
print("\n5. MONTHLY BREAKDOWN")
print("-" * 80)

# Ensure date is datetime type
combined_pdf['date'] = pd.to_datetime(combined_pdf['date'])

for month in [1, 2, 3]:
    month_name = ['January', 'February', 'March'][month-1]
    
    # PDF
    pdf_month = combined_pdf[
        (combined_pdf['date'].dt.month == month) & 
        (combined_pdf['date'].dt.year == 2025)
    ]
    
    # Ledger
    start_date = pd.to_datetime(f'2025-{month:02d}-01')
    end_date = pd.to_datetime(f'2025-{month+1:02d}-01') if month < 3 else pd.to_datetime('2025-04-01')
    ledger_month = stone_ledger[(stone_ledger['date'] >= start_date) & (stone_ledger['date'] < end_date)]
    
    print(f"\n{month_name} 2025:")
    print(f"  PDF:    {len(pdf_month):5} transactions")
    print(f"  Ledger: {len(ledger_month):5} transactions")
    if len(ledger_month) > 0:
        print(f"  Ratio:  {len(pdf_month)/len(ledger_month):.1f}x more in PDF")

print("\n" + "="*80)
print("ANALYSIS COMPLETE - Review results above")
print("="*80)
