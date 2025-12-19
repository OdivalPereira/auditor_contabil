import re
import os
import pandas as pd
from pypdf import PdfReader
from ofxparse import OfxParser
from datetime import datetime, timedelta
from decimal import Decimal

# --- CONFIG ---
PDF_LEDGER_PATH = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/diarios/Diário Banco do Brasil.pdf"
BANK_FILES_DIR = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/extratos"
REPORT_FILE = r"c:/Users/contabil/Documents/Projetos Antigravity/auditor_contabil/relatorio_final.md"

# --- HELPERS ---
def parse_br_amount(amount_str):
    clean_str = amount_str.replace('.', '').replace(',', '.')
    return Decimal(clean_str)

def parse_date(date_str):
    return datetime.strptime(date_str, "%d/%m/%Y").date()

# --- PARSERS ---
def parse_ledger(pdf_path):
    print(f"Parsing Ledger: {pdf_path}")
    reader = PdfReader(pdf_path)
    transactions = []
    
    current_date = None
    prev_balance = Decimal("0.00") 
    
    date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{4})$")
    balance_pattern = re.compile(r"^([\d\.]+,\d{2}[DC]?)") 
    
    full_text_lines = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text_lines.extend(text.split('\n'))
            
    i = 0
    while i < len(full_text_lines):
        line = full_text_lines[i].strip()
        
        if "Total" in line or "Saldo anterior" in line:
            i += 1
            continue

        date_match = date_pattern.match(line)
        if date_match:
            current_date = parse_date(date_match.group(1))
            i += 1
            continue
            
        balance_match = balance_pattern.match(line)
        if balance_match:
            bal_str = balance_match.group(1)
            if bal_str.endswith('D'):
                current_balance_val = parse_br_amount(bal_str[:-1])
            elif bal_str.endswith('C'):
                current_balance_val = -parse_br_amount(bal_str[:-1])
            else:
                current_balance_val = parse_br_amount(bal_str)
                
            diff = abs(current_balance_val - prev_balance)
            
            # Find value in line
            matches = list(re.finditer(r"([\d\.]+,\d{2})", line))
            found_amount = None
            
            # Strategy: Look for exact match of diff
            for m in matches:
                val = parse_br_amount(m.group(1))
                if val == diff:
                    found_amount = val
                    break
            
            # Fallback: If not found, take the second number (Debit/Credit column)
            if found_amount is None and len(matches) >= 2:
                 found_amount = parse_br_amount(matches[1].group(1))
            
            if found_amount is not None:
                amount = found_amount
                if current_balance_val > prev_balance:
                    final_amount = amount
                else:
                    final_amount = -amount
                
                # Extract Description
                desc = ""
                # Simple heuristic: text after the amount
                # A more robust way is to join lines until next date/balance
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
                    'description': desc.strip(),
                    'source': 'Ledger'
                })
            
            prev_balance = current_balance_val
        i += 1
        
    return pd.DataFrame(transactions)

def parse_bb_pdf(pdf_path):
    print(f"Parsing BB PDF: {pdf_path}")
    reader = PdfReader(pdf_path)
    transactions = []
    
    # Regex: Value | Sign | Date | Description
    txn_pattern = re.compile(r"^([\d\.]+,\d{2})\s*(\(\+\)|\(\-\))(\d{2}/\d{2}/\d{3,4})\s*(.*)")
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                match = txn_pattern.match(line)
                if match:
                    val_str = match.group(1)
                    sign_str = match.group(2)
                    date_str = match.group(3)
                    rest = match.group(4)
                    
                    amount = parse_br_amount(val_str)
                    if "(-)" in sign_str:
                        amount = -amount
                    
                    # Fix truncated date
                    if len(date_str) == 9:
                        date_str += "5"
                        
                    try:
                        dt = parse_date(date_str)
                        transactions.append({
                            'date': dt,
                            'amount': amount,
                            'description': rest,
                            'source': 'Bank'
                        })
                    except ValueError:
                        continue
    return pd.DataFrame(transactions)

def parse_ofx(file_path):
    print(f"Parsing OFX: {file_path}")
    transactions = []
    try:
        with open(file_path, encoding='latin-1') as fileobj:
            ofx = OfxParser.parse(fileobj)
            for t in ofx.account.statement.transactions:
                transactions.append({
                    'date': t.date.date(),
                    'amount': t.amount,
                    'description': t.memo,
                    'source': 'Bank'
                })
    except Exception as e:
        print(f"Error parsing OFX {file_path}: {e}")
    return pd.DataFrame(transactions)

# --- MAIN LOGIC ---
def main():
    # 1. Load Ledger
    df_ledger = parse_ledger(PDF_LEDGER_PATH)
    print(f"Total Ledger Transactions: {len(df_ledger)}")
    
    # 2. Load Bank
    bank_txns = []
    for root, dirs, files in os.walk(BANK_FILES_DIR):
        # Prioritize PDF for recent months, OFX for older
        # Actually, let's just load everything valid.
        # User said "ComprovanteBB" are the real ones.
        
        for f in files:
            path = os.path.join(root, f)
            if f.startswith('ComprovanteBB') and f.endswith('.pdf'):
                bank_txns.append(parse_bb_pdf(path))
            elif f.lower().endswith('.ofx') and 'BB' in f:
                bank_txns.append(parse_ofx(path))
                
    if bank_txns:
        df_bank = pd.concat(bank_txns, ignore_index=True)
    else:
        df_bank = pd.DataFrame()
        
    # 2.1 Filter Bank Transactions by Ledger Period
    if not df_ledger.empty:
        start_date = df_ledger['date'].min()
        end_date = df_ledger['date'].max()
        print(f"Ledger Period: {start_date} to {end_date}")
        
        df_bank = df_bank[
            (df_bank['date'] >= start_date) & 
            (df_bank['date'] <= end_date)
        ].copy()
        print(f"Bank Transactions (Filtered by Period): {len(df_bank)}")
    
    # 3. Reconcile (Strict 1-to-1 Matching)
    # We use a list of indices to track consumed transactions
    
    df_ledger['matched'] = False
    df_bank['matched'] = False
    
    # Sort for deterministic matching
    df_ledger = df_ledger.sort_values(by=['date', 'amount'])
    df_bank = df_bank.sort_values(by=['date', 'amount'])
    
    # Matching Loop
    # Iterate over Ledger and find first available match in Bank
    for l_idx, l_row in df_ledger.iterrows():
        # Find candidates in Bank: Same Date, Same Amount, Not Matched
        candidates = df_bank[
            (df_bank['date'] == l_row['date']) &
            (df_bank['amount'] == l_row['amount']) &
            (df_bank['matched'] == False)
        ]
        
        if not candidates.empty:
            b_idx = candidates.index[0]
            df_bank.at[b_idx, 'matched'] = True
            df_ledger.at[l_idx, 'matched'] = True
            
    # 4. Identify Discrepancies
    in_ledger_only = df_ledger[df_ledger['matched'] == False]
    in_bank_only = df_bank[df_bank['matched'] == False]
    
    print(f"In Ledger Only: {len(in_ledger_only)}")
    print(f"In Bank Only: {len(in_bank_only)}")
    
    # 5. Generate Report
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Relatório Final de Conciliação\n\n")
        f.write(f"**Data:** {datetime.now().strftime('%d/%m/%Y')}\n")
        f.write(f"**Total Diário:** {len(df_ledger)} | **Total Banco:** {len(df_bank)}\n\n")
        
        f.write("## 1. No Diário, mas NÃO no Banco (Faltam no Extrato ou Erro de Data)\n")
        f.write("| Data | Valor | Descrição |\n")
        f.write("|---|---|---|\n")
        for _, row in in_ledger_only.iterrows():
            f.write(f"| {row['date']} | {row['amount']} | {row['description']} |\n")
        f.write("\n")
        
        f.write("## 2. No Banco, mas NÃO no Diário (Faltam Lançar na Contabilidade)\n")
        f.write("| Data | Valor | Descrição |\n")
        f.write("|---|---|---|\n")
        for _, row in in_bank_only.iterrows():
            f.write(f"| {row['date']} | {row['amount']} | {row['description']} |\n")
        f.write("\n")
        
        f.write("## Resumo Financeiro\n")
        f.write(f"- **Soma 'Só no Diário':** {in_ledger_only['amount'].sum()}\n")
        f.write(f"- **Soma 'Só no Banco':** {in_bank_only['amount'].sum()}\n")
        
    print(f"Report generated: {REPORT_FILE}")

if __name__ == "__main__":
    main()
