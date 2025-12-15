import re
import os
import pandas as pd
from pypdf import PdfReader
from ofxparse import OfxParser
from datetime import datetime
from decimal import Decimal

# --- CONFIG ---
PDF_PATH = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/diarios/Diário Banco do Brasil.pdf"
OFX_DIR = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/extratos"
OUTPUT_CSV = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/reconciliacao_resultado.csv"

# --- HELPERS ---
def parse_br_amount(amount_str):
    """Converts '1.234,56' to Decimal(1234.56)"""
    clean_str = amount_str.replace('.', '').replace(',', '.')
    return Decimal(clean_str)

def parse_date(date_str):
    """Converts 'DD/MM/YYYY' to datetime"""
    return datetime.strptime(date_str, "%d/%m/%Y").date()

# --- PDF PARSER ---
def parse_ledger_pdf(pdf_path):
    print(f"Parsing Ledger: {pdf_path}")
    reader = PdfReader(pdf_path)
    transactions = []
    
    current_date = None
    prev_balance = Decimal("0.00") # Assuming starting balance 0 for logic, but will adjust
    
    # Regex
    date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{4})$")
    # Balance regex: matches "1.234,56D" or "0,00"
    balance_pattern = re.compile(r"^([\d\.]+,\d{2}[DC]?)") 
    
    full_text_lines = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text_lines.extend(text.split('\n'))
            
    # First pass to find opening balance if possible (optional, skipping for now)
    
    i = 0
    while i < len(full_text_lines):
        line = full_text_lines[i].strip()
        
        # Check Date
        date_match = date_pattern.match(line)
        if date_match:
            current_date = parse_date(date_match.group(1))
            i += 1
            continue
            
        # Check Transaction Line (starts with Balance)
        balance_match = balance_pattern.match(line)
        if balance_match:
            bal_str = balance_match.group(1)
            
            # Parse Balance
            if bal_str.endswith('D'):
                current_balance = -parse_br_amount(bal_str[:-1]) # Debit is negative in accounting? Or positive? 
                # Usually in Bank Statements: Credit (+), Debit (-).
                # In Ledger (Asset account): Debit (+), Credit (-).
                # Let's stick to: D = Debit, C = Credit.
                # We need to be consistent with OFX.
                # OFX: Payment is negative, Deposit is positive.
                # Ledger (Bank Account): Debit = Increase (Deposit), Credit = Decrease (Payment).
                # So D = +, C = -.
                current_balance_val = parse_br_amount(bal_str[:-1])
            elif bal_str.endswith('C'):
                current_balance_val = -parse_br_amount(bal_str[:-1])
            else:
                current_balance_val = parse_br_amount(bal_str) # 0,00
                
            # Calculate Diff (Transaction Value)
            # We need absolute difference to find the value string
            diff = abs(current_balance_val - prev_balance)
            
            # Format diff to string to search in line (e.g. 2.000,00)
            # This is tricky because of thousands separators.
            # Let's try to find all numbers in the line and see which one matches the diff.
            
            # Extract all potential values from line
            # Regex for values: digits, dots, comma, 2 digits
            potential_values = re.findall(r"([\d\.]+,\d{2})", line)
            
            found_value = None
            desc_start_index = -1
            
            # The first match is the Balance itself. Skip it.
            # But wait, potential_values will contain the balance number too.
            
            for val_str in potential_values:
                val_dec = parse_br_amount(val_str)
                # Check if this value matches the diff (with some tolerance for float math, though Decimal is exact)
                if val_dec == diff:
                    found_value = val_dec
                    # Find where this value ends in the line to start description
                    # Be careful if the same value appears twice (Balance and Amount same?)
                    # If Balance is 20,00D and Amount is 20,00.
                    pass
            
            # If we didn't find exact match, maybe the prev_balance logic is off (e.g. first line).
            # Fallback: Assume the value is the second number in the line?
            # Or use the heuristic: Balance is first, Value is second (if present), or Value is embedded.
            
            # Let's use the "Diff" method primarily.
            if found_value is not None:
                amount = found_value
                # Determine sign
                # If Balance went from 0 to 2000D (Increase), it's a Debit (Deposit).
                # If Balance went from 2000D to 1000D (Decrease), it's a Credit (Payment).
                
                # Actually, let's just capture the D/C of the transaction if possible.
                # But the line doesn't explicitly say D/C for the transaction value, only for the balance.
                # We infer transaction type from balance change.
                # Increase in Debit Balance -> Debit Transaction.
                # Decrease in Debit Balance -> Credit Transaction.
                # Increase in Credit Balance -> Credit Transaction.
                # Decrease in Credit Balance -> Debit Transaction.
                
                is_debit = False
                if current_balance_val > prev_balance:
                    is_debit = True # Debit transaction (Deposit)
                else:
                    is_debit = False # Credit transaction (Payment)
                
                final_amount = amount if is_debit else -amount
                
                # Extract Description
                # Find the substring of the value in the line, and take everything after it.
                # Need to be careful about multiple occurrences.
                # We know the Balance is at the start.
                val_str_formatted = f"{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                # The above formatting might not match exactly (e.g. 1.000,00 vs 1000,00).
                # Better to find the substring that parsed to 'amount'.
                
                # Let's assume the value is the one we found in potential_values.
                # We iterate potential_values again and find the index.
                
                # Hacky: split line by the value string.
                # But we need the exact string representation from the line.
                
                # Let's just take the text after the Balance and "Key".
                # Regex: ^BalanceStr \s* (KeyStr)? \s* ValueStr \s* (Description)
                
                # Construct regex dynamically? No.
                
                # Let's use the text remaining after removing Balance and Value.
                
                # Find the value string in the line that matches our amount
                # We search for the string that we parsed.
                
                matches = re.finditer(r"([\d\.]+,\d{2})", line)
                val_match = None
                for m in matches:
                    if parse_br_amount(m.group(1)) == amount:
                        # We found the value.
                        # Ensure it's not the balance (unless balance == value, which happens if prev=0)
                        # If prev=0, Balance=2000, Value=2000.
                        # The line will have "2.000,00D... 2.000,00..."
                        # So we want the *second* match if they are equal?
                        # Or just the match that is NOT at the start (index 0)?
                        if m.start() > 0: 
                            val_match = m
                            break
                        elif m.start() == 0 and prev_balance == 0:
                             # If balance is at start, look for another one?
                             # In "20,00D20,00...", the first 20,00 is part of 20,00D.
                             # The second 20,00 is the value.
                             pass
                
                # If we still haven't found a distinct value match (e.g. "20,00D20,00"), 
                # we need to be smart.
                
                # Let's try to split the line after the Balance.
                line_no_bal = line[len(bal_str):]
                # Now search for value in line_no_bal
                m2 = re.search(r"([\d\.]+,\d{2})", line_no_bal)
                if m2 and parse_br_amount(m2.group(1)) == amount:
                    desc = line_no_bal[m2.end():].strip()
                    # Check for subsequent lines
                    j = i + 1
                    while j < len(full_text_lines):
                        next_line = full_text_lines[j].strip()
                        if date_pattern.match(next_line) or balance_pattern.match(next_line):
                            break
                        desc += " " + next_line
                        j += 1
                    
                    transactions.append({
                        'date': current_date,
                        'amount': final_amount,
                        'description': desc,
                        'source': 'Ledger'
                    })
            
            prev_balance = current_balance_val
            
        i += 1
        
    return pd.DataFrame(transactions)

# --- OFX PARSER ---
def parse_ofx_files(ofx_dir):
    transactions = []
    print(f"Parsing OFX files in: {ofx_dir}")
    for root, dirs, files in os.walk(ofx_dir):
        for filename in files:
            if filename.lower().endswith('.ofx') and 'BB' in filename: # Filter for BB
                filepath = os.path.join(root, filename)
                try:
                    with open(filepath, encoding='latin-1') as fileobj:
                        ofx = OfxParser.parse(fileobj)
                        for t in ofx.account.statement.transactions:
                            transactions.append({
                                'date': t.date.date(),
                                'amount': t.amount, # OFX: - is debit (payment), + is credit (deposit)
                                'description': t.memo,
                                'source': 'Bank'
                            })
                except Exception as e:
                    print(f"Error parsing {filename}: {e}")
                    
    return pd.DataFrame(transactions)

# --- MAIN ---
def main():
    # 1. Parse Ledger
    df_ledger = parse_ledger_pdf(PDF_PATH)
    print(f"Ledger Transactions: {len(df_ledger)}")
    if not df_ledger.empty:
        print(df_ledger.head())
        # Normalize Ledger Amounts to match OFX
        # Ledger: D = +, C = - (based on my logic above)
        # OFX: D = -, C = + (Standard Bank Statement)
        # Wait, Bank Statement:
        # Deposit = Credit (+)
        # Payment = Debit (-)
        # Ledger (Bank Account in Assets):
        # Deposit = Debit (+)
        # Payment = Credit (-)
        
        # So:
        # Ledger Debit (+) should match OFX Credit (+)
        # Ledger Credit (-) should match OFX Debit (-)
        
        # So the signs should MATCH if I parsed Ledger D as + and C as -.
        # Let's verify.
        pass

    # 2. Parse OFX
    df_bank = parse_ofx_files(OFX_DIR)
    print(f"Bank Transactions: {len(df_bank)}")
    if not df_bank.empty:
        print(df_bank.head())

    # 3. Reconcile
    if df_ledger.empty or df_bank.empty:
        print("No data to reconcile.")
        return

    # Create keys for matching
    # We match on Date and Amount.
    # Since descriptions vary wildy, we ignore them for matching initially.
    
    # Add ID to track usage
    df_ledger['id'] = df_ledger.index
    df_bank['id'] = df_bank.index
    
    matched_ledger_ids = set()
    matched_bank_ids = set()
    
    matches = []
    
    # Iterate through Ledger and try to find match in Bank
    for idx, row in df_ledger.iterrows():
        # Filter bank candidates
        candidates = df_bank[
            (df_bank['date'] == row['date']) & 
            (df_bank['amount'] == row['amount']) &
            (~df_bank.index.isin(matched_bank_ids))
        ]
        
        if not candidates.empty:
            # Take the first match
            match_idx = candidates.index[0]
            matched_bank_ids.add(match_idx)
            matched_ledger_ids.add(idx)
            matches.append((idx, match_idx))
            
    # Identify Unmatched
    unmatched_ledger = df_ledger[~df_ledger.index.isin(matched_ledger_ids)].copy()
    unmatched_bank = df_bank[~df_bank.index.isin(matched_bank_ids)].copy()
    
    unmatched_ledger['status'] = 'In Ledger Only'
    unmatched_bank['status'] = 'In Bank Only'
    
    # Combine results
    result = pd.concat([unmatched_ledger, unmatched_bank], ignore_index=True)
    
    # Sort
    result = result.sort_values(by='date')
    
    # Save
    result.to_csv(OUTPUT_CSV, index=False)
    print(f"Reconciliation complete. Saved to {OUTPUT_CSV}")
    print(f"Unmatched Ledger: {len(unmatched_ledger)}")
    print(f"Unmatched Bank: {len(unmatched_bank)}")

if __name__ == "__main__":
    main()
