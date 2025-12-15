import pdfplumber
import re
from datetime import datetime
import ftfy

def parse_amount(amount_str):
    """Parses amount string '3.000,00' to float 3000.00."""
    clean_amt = amount_str.replace('.', '').replace(',', '.')
    return float(clean_amt)

class BaseParser:
    def parse(self, pdf):
        raise NotImplementedError

class BBParser(BaseParser):
    def parse(self, pdf):
        transactions = []
        account_info = {
            'bank_id': '001', 
            'branch_id': '',
            'acct_id': ''
        }
        
        line_pattern = re.compile(r'^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+([\d\.]+,\d{2})\s+([CD])')
        acct_pattern = re.compile(r'(\d{4}-[\w])\s+\d+\s+([\d\.\-]+)')

        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue
            
            text = ftfy.fix_text(text)
            lines = text.split('\n')
            
            current_transaction = None
            
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
                    amount = parse_amount(amount_str)
                    if type_str == 'D':
                        amount = -amount
                    
                    if "Saldo anterior" in raw_desc:
                        continue

                    parts = raw_desc.split()
                    doc_id = ""
                    memo = raw_desc
                    
                    if len(parts) > 1 and re.match(r'^\d+$', parts[-1]) and len(parts[-1]) > 6:
                        doc_id = parts[-1]
                        memo = " ".join(parts[:-1])
                    
                    trn_type = 'DEP' if amount > 0 else 'DEBIT'
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

class SicrediParser(BaseParser):
    def parse(self, pdf):
        transactions = []
        account_info = {
            'bank_id': '748', # Sicredi
            'branch_id': '',
            'acct_id': ''
        }
        
        # Regex for Sicredi: 01/04/2025 ...
        date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{4})')
        
        # Header detection for columns (approximate x positions)
        # Based on visual inspection of typical Sicredi:
        # Date: Left
        # Doc: ~80
        # Hist: ~150
        # Debit: ~400
        # Credit: ~480
        # Balance: ~550
        
        for page in pdf.pages:
            # Extract words to get positions
            words = page.extract_words()
            
            # Extract text for account info (easier with text)
            text = page.extract_text()
            if text:
                text = ftfy.fix_text(text)
                # Account info pattern: "SAGRADO SABOR LTDA 000091882-7"
                # Or just look for the pattern \d{9}-\d
                if not account_info['acct_id']:
                    acct_match = re.search(r'(\d{5,9}-\d)', text)
                    if acct_match:
                        account_info['acct_id'] = acct_match.group(1)
            
            # Process lines based on Y coordinate clustering
            # Simple approach: Group words by 'top' coordinate
            lines = {}
            for w in words:
                top = round(w['top'])
                if top not in lines:
                    lines[top] = []
                lines[top].append(w)
            
            sorted_y = sorted(lines.keys())
            
            for y in sorted_y:
                line_words = sorted(lines[y], key=lambda x: x['x0'])
                line_text = " ".join([w['text'] for w in line_words])
                line_text = ftfy.fix_text(line_text)
                
                # Check if line starts with date
                match = date_pattern.match(line_text)
                if match:
                    date_str = match.group(1)
                    dt = datetime.strptime(date_str, '%d/%m/%Y')
                    
                    # Identify amounts based on X position
                    # We need to find numbers at the end of the line
                    # And check their X position to determine Debit vs Credit
                    
                    # Filter words that look like amounts
                    amount_words = []
                    for w in line_words:
                        # Clean text to check if number
                        txt = w['text'].replace('.', '').replace(',', '.')
                        try:
                            float(txt)
                            # It's a number. Check if it's a date or doc?
                            if '/' in w['text']: continue
                            if len(w['text']) < 3: continue # Skip small numbers like '007' if not amount formatted
                            if ',' in w['text']: # Amounts usually have comma
                                amount_words.append(w)
                        except:
                            pass
                    
                    if not amount_words:
                        continue
                        
                    # Logic:
                    # If 1 amount: Check X. 
                    # If 2 amounts: First is transaction, second is balance.
                    
                    trn_amount = 0.0
                    trn_type = 'DEBIT' # Default
                    
                    # Heuristic X coordinates (need calibration)
                    # Page width is usually ~595 for A4
                    # Debit ~ 350-450?
                    # Credit ~ 450-520?
                    # Balance ~ 520+?
                    
                    # Let's use the last amount word if it's the only one, or second to last if there are two
                    # Wait, if there is a balance, it's the last one.
                    
                    # Better: Classify each amount word by X
                    # Debit X < 460 (approx)
                    # Credit X >= 460 (approx)
                    
                    # Let's look at the dump again to guess.
                    # "DEBITO CREDITO SALDO"
                    # They are usually right aligned.
                    
                    primary_amt_word = amount_words[0]
                    
                    # If there are multiple amounts, the last one might be balance.
                    # But sometimes we have Debit AND Balance, or Credit AND Balance.
                    # Sometimes just Debit (no balance shown).
                    
                    # Let's try to detect column headers? No, too complex for now.
                    # Let's use a threshold.
                    
                    x_mid = 460 # Threshold between Debit and Credit columns
                    
                    val = parse_amount(primary_amt_word['text'])
                    x_pos = primary_amt_word['x0']
                    
                    if x_pos < x_mid:
                        trn_amount = -val
                        trn_type = 'DEBIT'
                    else:
                        trn_amount = val
                        trn_type = 'DEP'
                        
                    # Description is everything between date and amount
                    # Reconstruct desc
                    desc_words = [w['text'] for w in line_words if w['x0'] > 50 and w['x0'] < primary_amt_word['x0']]
                    memo = " ".join(desc_words)
                    memo = ftfy.fix_text(memo)
                    
                    # Refine type
                    lower_memo = memo.lower()
                    if 'pix' in lower_memo:
                        # Check header keywords if X logic fails?
                        pass
                        
                    fitid = f"{dt.strftime('%Y%m%d')}{int(abs(trn_amount)*100):010d}{len(transactions)}"
                    
                    transactions.append({
                        'date': dt,
                        'amount': trn_amount,
                        'type': trn_type,
                        'memo': memo,
                        'fitid': fitid,
                        'checknum': ''
                    })

        return transactions, account_info

def get_parser(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        first_page_text = pdf.pages[0].extract_text()
        if not first_page_text:
            return None
            
        if "Banco do Brasil" in first_page_text or "SISBB" in first_page_text:
            return BBParser()
        elif "SICREDI" in first_page_text or "COOP CRED" in first_page_text:
            return SicrediParser()
        else:
            # Default fallback or error
            return None

def parse_pdf(file_obj):
    # We need to read the file to detect type, but pdfplumber expects path or file-like.
    # If file_obj is a BytesIO, we can just pass it.
    
    # But get_parser opens it. We shouldn't open it twice if it's a stream (cursor moves).
    # So let's instantiate pdfplumber once.
    
    with pdfplumber.open(file_obj) as pdf:
        first_page_text = pdf.pages[0].extract_text() or ""
        
        parser = None
        if "Banco do Brasil" in first_page_text or "SISBB" in first_page_text:
            parser = BBParser()
        elif "SICREDI" in first_page_text or "COOP CRED" in first_page_text:
            parser = SicrediParser()
            
        if parser:
            return parser.parse(pdf)
        else:
            raise ValueError("Bank layout not recognized.")

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
    body += tag("ORG", "Banco do Brasil S/A" if account_info['bank_id'] == '001' else "Sicredi", 3)
    body += tag("FID", account_info['bank_id'], 3)
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
    
    # Sicredi (748) specific formatting:
    # - No BRANCHID tag
    # - ACCTID includes Agency + Account
    if account_info['bank_id'] == '748':
        # Clean IDs
        branch = account_info['branch_id'].replace('-', '').replace('.', '')
        acct = account_info['acct_id'].replace('-', '').replace('.', '')
        
        # Concatenate Agency + Account for ACCTID
        # Example suggests: Agency (no leading zero?) + Account
        # But let's just concatenate what we have for now.
        full_acct_id = f"{branch}{acct}"
        body += tag("ACCTID", full_acct_id, 5)
    else:
        # Standard behavior (e.g. Banco do Brasil)
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
