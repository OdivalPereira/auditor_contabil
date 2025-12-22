import pdfplumber
from src.parsing.banks.sicoob import SicoobPDFParser

p = SicoobPDFParser()
f = r'extração_pdfs/pdf_modelos/Extrato Sicoob 10.2025.pdf'
pdf = pdfplumber.open(f)

print("Comparing diagnostic (reset method) vs parser (accumulate method)")
print("="*80)

# Method 1: Diagnostic - Reset at each SALDO DO DIA (like my step diagnostic)
running_bal = 20883.58
for i, page in enumerate(pdf.pages):
    txns, bs, be = p.extract_page(page)
    page_sum = sum(t['amount'] for t in txns)
    
    if be is not None:  # Page has SALDO DO DIA
        # Reset to the balance shown
        running_bal = be
        if i < 5:  # Show first 5 pages
            print(f"Page {i+1}: {len(txns)} txns, sum={page_sum:>10.2f}, RESET to {be:>10.2f}")
    else:
        # No SALDO, just accumulate
        running_bal += page_sum
        if i < 5:
            print(f"Page {i+1}: {len(txns)} txns, sum={page_sum:>10.2f}, running={running_bal:>10.2f}")

print(f"\nDiagnostic Final Balance (with resets): {running_bal:.2f}")

# Method 2: Parser - Pure accumulation
df, m = p.parse(f)
calc_bal = 20883.58 + df.amount.sum()
print(f"Parser Final Balance (pure sum): {calc_bal:.2f}")
print(f"Expected Final Balance: 201651.64")
print(f"\nDifference (Parser - Expected): {calc_bal - 201651.64:.2f}")
