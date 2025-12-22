import pdfplumber
import re
from src.parsing.banks.sicoob import SicoobPDFParser
from datetime import datetime

p = SicoobPDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
pdf = pdfplumber.open(f)

# Extract daily balances from PDF text
daily_bals = []
for i, page in enumerate(pdf.pages):
    text = page.extract_text()
    # Find patterns like 01/10/2025... SALDO DO DIA 6.225,10C
    # Actually, the date might be far above. 
    # Let's just catch all SALDO DO DIA and the amount.
    matches = re.findall(r"SALDO DO DIA\s+([\d\.,]+)([CD])", text)
    if matches:
        # We need the date too. Let's look for the last date before the match.
        dates = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
        if dates:
            dt = dates[-1]
            val = p._parse_sicoob_amount(matches[-1][0] + matches[-1][1])
            daily_bals.append((dt, val))

print("Daily Balances found in PDF:")
for dt, val in daily_bals:
    print(f"{dt}: {val:.2f}")

# Parse transactions
df, m = p.parse(f)
df['date_str'] = df['date'].apply(lambda x: x.strftime('%d/%m/%Y'))

print("\nComparison:")
prev_b = 20883.58
for dt_str, target_b in daily_bals:
    # Sum of transactions up to this date
    # Wait, Sicoob might have multiple pages per date.
    # Let's just check the cumulative sum up to the LAST transaction of that date.
    relevant_tx = df[df.date_str <= dt_str]
    calc_b = 20883.58 + relevant_tx.amount.sum()
    print(f"Date {dt_str}: Target {target_b:.2f}, Calc {calc_b:.2f}, Diff {calc_b - target_b:.2f}")
