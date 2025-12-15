import pdfplumber
import re
import os
from datetime import datetime

def parse_amount(amount_str, type_str):
    """Parses amount string '3.000,00' to float 3000.00.
    Returns positive for Credit, negative for Debit."""
    clean_amt = amount_str.replace('.', '').replace(',', '.')
    val = float(clean_amt)
    if type_str == 'D':
        val = -val
    return val

def parse_pdf(pdf_path):
    transactions = []
    account_info = {
        'bank_id': '001', 
        'branch_id': '',
        'acct_id': ''
    }
    
    # Regex patterns
    line_pattern = re.compile(r'^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+([\d\.]+,\d{2})\s+([CD])')
    acct_pattern = re.compile(r'(\d{4}-[\w])\s+\d+\s+([\d\.\-]+)')

    with pdfplumber.open(pdf_path) as pdf:
        current_transaction = None
        
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
                
            lines = text.split('\n')
            for line in lines:
                if not account_info['acct_id']:
                    acct_match = acct_pattern.search(line)
                    if acct_match:
                        account_info['branch_id'] = acct_match.group(1)
                        account_info['acct_id'] = acct_match.group(2)

                match = line_pattern.match(line)
                if match:
                    date_str, raw_desc, amount_str, type_str = match.groups()
                    dt = datetime.strptime(date_str, '%d.%m.%Y')
                    amount = parse_amount(amount_str, type_str)
                    
                    # Filter out "Saldo anterior"
                    if "Saldo anterior" in raw_desc:
                        continue

                    parts = raw_desc.split()
                    doc_id = ""
                    memo = raw_desc
                    
                    if len(parts) > 1 and re.match(r'^\d+$', parts[-1]) and len(parts[-1]) > 6:
                        doc_id = parts[-1]
                        memo = " ".join(parts[:-1])
                    
                    # Determine Transaction Type
                    trn_type = 'DEBIT'
                    if amount > 0:
                        trn_type = 'DEP'
                    
                    lower_memo = memo.lower()
                    if 'transfer' in lower_memo or 'ted' in lower_memo or 'doc' in lower_memo or 'pix' in lower_memo:
                         if 'transfer' in lower_memo:
                             trn_type = 'XFER'
                    if 'saque' in lower_memo:
                        trn_type = 'CASH'

                    fitid = f"{dt.strftime('%Y%m%d')}{int(abs(amount)*100):010d}{len(transactions)}"
                    
                    current_transaction = {
                        'date': dt,
                        'amount': amount,
                        'type': trn_type,
                        'memo': memo,
                        'fitid': doc_id if (doc_id and doc_id.isdigit()) else fitid,
                        'checknum': doc_id
                    }
                    transactions.append(current_transaction)
                
                elif current_transaction:
                    ignore_keywords = ["Extrato de Conta", "Conta Corrente", "Nome", "Data Dia", "Saldo anterior", "S A L D O", "Agência", "Mod. 0.51", "TABLE CONTENT", "--- Page"]
                    if any(keyword in line for keyword in ignore_keywords):
                        continue
                    if '|' in line:
                        continue
                    if len(line.strip()) < 3:
                        continue
                    current_transaction['memo'] += " " + line.strip()

    return transactions, account_info

def generate_ofx(transactions, account_info):
    header = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE
"""
    
    now_date = datetime.now().strftime('%Y%m%d') # YYYYMMDD
    
    # Indentation helper
    def tag(name, content, indent=0, close=False):
        sp = " " * indent
        if close:
            return f"{sp}<{name}>{content}</{name}>\n"
        return f"{sp}<{name}>{content}\n"
        
    def open_tag(name, indent=0):
        sp = " " * indent
        return f"{sp}<{name}>\n"
        
    def close_tag(name, indent=0):
        sp = " " * indent
        return f"{sp}</{name}>\n"

    body = "<OFX>\n"
    
    # SIGNONMSGSRSV1
    body += open_tag("SIGNONMSGSRSV1", 0)
    body += open_tag("SONRS", 1)
    body += open_tag("STATUS", 2)
    body += tag("CODE", "0", 3, close=True)
    body += tag("SEVERITY", "INFO", 3, close=True)
    body += close_tag("STATUS", 2)
    body += tag("DTSERVER", now_date, 2)
    body += tag("LANGUAGE", "POR", 2)
    body += tag("DTACCTUP", now_date, 2)
    body += open_tag("FI", 2)
    body += tag("ORG", "Banco do Brasil S/A", 3)
    body += tag("FID", "001", 3)
    body += close_tag("FI", 2)
    body += close_tag("SONRS", 1)
    body += close_tag("SIGNONMSGSRSV1", 0)
    
    # BANKMSGSRSV1
    body += open_tag("BANKMSGSRSV1", 0)
    body += open_tag("STMTTRNRS", 1)
    body += tag("TRNUID", "0", 2)
    body += open_tag("STATUS", 3)
    body += tag("CODE", "0", 4, close=True)
    body += tag("SEVERITY", "INFO", 4, close=True)
    body += close_tag("STATUS", 3)
    
    body += open_tag("STMTRS", 3)
    body += tag("CURDEF", "BRL", 4)
    
    body += open_tag("BANKACCTFROM", 4)
    body += tag("BANKID", account_info['bank_id'], 5)
    if account_info['branch_id']:
        body += tag("BRANCHID", account_info['branch_id'], 5)
    body += tag("ACCTID", account_info['acct_id'], 5)
    body += tag("ACCTTYPE", "CHECKING", 5)
    body += close_tag("BANKACCTFROM", 4)
    
    body += open_tag("BANKTRANLIST", 4)
    body += tag("DTSTART", transactions[0]['date'].strftime('%Y%m%d'), 5)
    body += tag("DTEND", transactions[-1]['date'].strftime('%Y%m%d'), 5)
    
    for trn in transactions:
        dt_posted = trn['date'].strftime('%Y%m%d')
        body += open_tag("STMTTRN", 5)
        body += tag("TRNTYPE", trn['type'], 6)
        body += tag("DTPOSTED", dt_posted, 6)
        body += tag("TRNAMT", f"{trn['amount']:.2f}", 6)
        body += tag("FITID", trn['fitid'], 6)
        if trn['checknum']:
            body += tag("CHECKNUM", trn['checknum'], 6)
        body += tag("MEMO", trn['memo'], 6)
        body += close_tag("STMTTRN", 5)

    body += close_tag("BANKTRANLIST", 4)
    
    body += open_tag("LEDGERBAL", 4)
    body += tag("BALAMT", "0.00", 5)
    body += tag("DTASOF", now_date, 5)
    body += close_tag("LEDGERBAL", 4)
    
    body += close_tag("STMTRS", 3)
    body += close_tag("STMTTRNRS", 1)
    body += close_tag("BANKMSGSRSV1", 0)
    body += "</OFX>\n"
    
    return header + body

if __name__ == "__main__":
    pdf_path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs\pdf_modelos\MCM set25.pdf"
    ofx_path = r"c:\Users\contabil\Documents\Projetos Antigravity\extração_pdfs\output.ofx"
    
    try:
        print("Parsing PDF...")
        transactions, acct_info = parse_pdf(pdf_path)
        print(f"Found {len(transactions)} transactions.")
        print(f"Account Info: {acct_info}")
        
        print("Generating OFX...")
        ofx_content = generate_ofx(transactions, acct_info)
        
        with open(ofx_path, "w", encoding="utf-8") as f:
            f.write(ofx_content)
            
        print(f"OFX file created at {ofx_path}")
        
    except Exception as e:
        print(f"Error: {e}")
