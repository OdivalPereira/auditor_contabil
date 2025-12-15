
import logging
import pandas as pd
import pdfplumber
import re
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)

class ItauPDFParser(BaseParser):
    """
    Parser for Itaú monthly statement PDFs.
    
    Layouts:
    1. Full Date: 27/10/2025 ...
    2. Short Date: 03 / fev ... (Need header year)
    """

    MONTH_MAP = {
        'jan': 1, 'fev': 2, 'mar': 3, 'abr': 4, 'mai': 5, 'jun': 6,
        'jul': 7, 'ago': 8, 'set': 9, 'out': 10, 'nov': 11, 'dez': 12
    }

    def _parse_text_fallback(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        metadata = {
            'bank': 'Itau', 
            'agency': '', 
            'account': '', 
            'start_date': None, 
            'end_date': None
        }
        transactions = []
        
        try:
            with pdfplumber.open(file_path_or_buffer) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
            
            lines = full_text.split('\n')
            
            # 1. Extract Metadata & Years
            # Look for period line: "período: 01/02/2025 até 28/02/2025"
            period_match = re.search(r"período:?\s+(\d{2}/\d{2}/\d{4})\s+at[ée]\s+(\d{2}/\d{2}/\d{4})", full_text, re.IGNORECASE)
            
            ref_year = datetime.now().year # Fallback
            ref_years_map = {} # month -> year
            
            if period_match:
                start_str, end_str = period_match.groups()
                try:
                    start_dt = datetime.strptime(start_str, "%d/%m/%Y")
                    end_dt = datetime.strptime(end_str, "%d/%m/%Y")
                    metadata['start_date'] = start_dt.date()
                    metadata['end_date'] = end_dt.date()
                    
                    # Build map for Short Date parsing
                    # If period spans Dec 2024 to Jan 2025
                    curr = start_dt
                    while curr <= end_dt:
                        ref_years_map[curr.month] = curr.year
                        # Advance month logic roughly (not critical to be perfect loop)
                        if curr.month == 12:
                            curr = curr.replace(year=curr.year+1, month=1)
                        else:
                            curr = curr.replace(month=curr.month+1)
                            
                    ref_year = end_dt.year # Default fallback
                except:
                    pass
            
            # Account info
            # "Agência 8496 Conta 0099497-4" or "02.675.877/0001-08 0464 18521-4"
            # Try specific label first
            ag_match = re.search(r"Agência\s+(\d+)\s+Conta\s+([\d\-]+)", full_text, re.IGNORECASE)
            if ag_match:
                metadata['agency'] = ag_match.group(1)
                metadata['account'] = ag_match.group(2)
            
            if ag_match:
                metadata['agency'] = ag_match.group(1)
                metadata['account'] = ag_match.group(2)
                
            # Balance Header Extraction
            # Look for: "Saldo total ... R$ X.XXX,XX"
            # Multiline regex to catch values below headers
            if 'balance_end' not in metadata:
                # Itaú Header: 
                # Saldo total ...
                # R$ 1.840,87 ...
                # We try to grab the first R$ value after "Saldo total"
                header_bal_match = re.search(r"Saldo total.*?R\$\s*([\d\.]+,\d{2})", full_text, re.DOTALL | re.IGNORECASE)
                if header_bal_match:
                     metadata['balance_end'] = self._parse_br_amount(header_bal_match.group(1))
                     # Usually positive in this header unless minus sign
                     if '-' in header_bal_match.group(0): # Check overlapping context for sign?
                         # R$ -10,00
                         pass 
                     # Refine: check precise match
                     if "R$ -" in header_bal_match.group(0) or "R$ -" in full_text[header_bal_match.start():header_bal_match.end()]:
                         metadata['balance_end'] = -metadata['balance_end']
            
            # 2. Parse Lines
            
            # Regex A: Full Date
            # 27/10/2025 ... 21,00
            # Allow optional minus (standard and unicode) and spaces in amount group
            regex_full = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.*?)\s+([\-\u2013\u2014\s]*[\d\.]+,\d{2})")
            
            # Regex B: Short Date
            # 03 / fev ... -16,33
            regex_short = re.compile(r"^(\d{2})\s*/\s*([a-z]{3})\s+(.*?)\s+([\-\u2013\u2014\s]*[\d\.]+,\d{2})", re.IGNORECASE)

            for line in lines:
                line = line.strip()
                
                # Check for Balance Lines (that might have been skipped or parsed)
                if "SALDO ANTERIOR" in line.upper():
                     # Usually 30/09/2025 SALDO ANTERIOR 0,00
                     # Could be parsed as transaction or not.
                     # Pattern: Date ... SALDO ANTERIOR ... Amount
                     match_bal = re.search(r"SALDO ANTERIOR.*?([\-\u2013\u2014\s]*[\d\.]+,\d{2})", line, re.IGNORECASE)
                     if match_bal:
                         start_val = self._parse_br_amount(match_bal.group(1).replace(" ", ""))
                         if '-' in match_bal.group(1): 
                             start_val = -start_val
                         metadata['balance_start'] = start_val
                             
                if "SALDO FINAL" in line.upper() or "SALDO DISPONIVEL" in line.upper().replace("Í", "I").replace("í", "i"):
                     match_bal = re.search(r"([\-\u2013\u2014\s]*[\d\.]+,\d{2})", line)
                     if match_bal:
                         val = self._parse_br_amount(match_bal.group(1).replace(" ", ""))
                         if '-' in match_bal.group(1): val = -val
                         metadata['balance_end'] = val

                if self.should_ignore_line(line):
                    continue
                
                dt = None
                desc = ""
                amount = 0.0
                
                # Try Full Date
                match_full = regex_full.match(line)
                if match_full:
                    date_str = match_full.group(1)
                    desc = match_full.group(2).strip()
                    amount_str = match_full.group(3)
                    
                    try:
                        dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                        amount = self._parse_br_amount(amount_str.replace(" ", ""))
                    except:
                        pass
                
                # Try Short Date
                elif regex_short.match(line):
                    match_short = regex_short.match(line)
                    day_str = match_short.group(1)
                    mon_str = match_short.group(2).lower()
                    desc = match_short.group(3).strip()
                    amount_str = match_short.group(4)
                    
                    if mon_str in self.MONTH_MAP:
                        month_num = self.MONTH_MAP[mon_str]
                        year = ref_years_map.get(month_num, ref_year)
                        try:
                            dt = datetime(year, month_num, int(day_str)).date()
                            amount = self._parse_br_amount(amount_str.replace(" ", ""))
                        except:
                            pass
                
                # Check for Balance Lines (that might have been skipped or parsed)
                if "SALDO ANTERIOR" in line.upper():
                     # Usually 30/09/2025 SALDO ANTERIOR 0,00
                     # Could be parsed as transaction or not.
                     # Pattern: Date ... SALDO ANTERIOR ... Amount
                     match_bal = re.search(r"SALDO ANTERIOR.*?([\-\u2013\u2014\s]*[\d\.]+,\d{2})", line, re.IGNORECASE)
                     if match_bal:
                         metadata['balance_start'] = self._parse_br_amount(match_bal.group(1).replace(" ", ""))
                         # Sign might be negative if explicitly has minus, parsed by _parse_br_amount usually returns abs if not careful?
                         # BaseParser._parse_br_amount returns ABS. We need to check sign.
                         if '-' in match_bal.group(1):
                             metadata['balance_start'] = -metadata['balance_start']
                             
                if "SALDO FINAL" in line.upper() or "SALDO DISPONIVEL" in line.upper().replace("Í", "I").replace("í", "i"):
                     match_bal = re.search(r"([\-\u2013\u2014\s]*[\d\.]+,\d{2})", line)
                     if match_bal:
                         val = self._parse_br_amount(match_bal.group(1).replace(" ", ""))
                         if '-' in match_bal.group(1): val = -val
                         metadata['balance_end'] = val

                if dt and amount != 0.0:
                    # Heuristic Direction Correction
                    # Itaú CSV/PDF sometimes separates signs or omits them in specific layouts
                    # Enforce negativity for clear debit keywords
                    desc_upper = desc.upper()
                    if any(k in desc_upper for k in ["JUROS", "MULTA", "TAR ", "TARIFA", "IOF", "PAGTO", "PAGAMENTO", "SAQUE", "RENEGOCIA"]):
                        if amount > 0:
                            amount = -amount
                    
                    # Enforce positivity for clear credit keywords (optional, mostly trusted usually)
                    # if any(k in desc_upper for k in ["RECEBIDO", "CRED", "RESGATE"]):
                    #     amount = abs(amount)

                    transactions.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc,
                        'source': 'Bank'
                    })

                if dt and amount != 0.0:
                    transactions.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc,
                        'source': 'Bank'
                    })
        except Exception as e:
            pass # Fallback
            
        return transactions, metadata

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        metadata = {
            'bank': 'Itau', 
            'agency': '', 
            'account': '', 
            'start_date': None, 
            'end_date': None,
            'balance_start': None,
            'balance_end': None
        }
        
        # Try Coordinate Parsing first (most robust for columns)
        try:
             with pdfplumber.open(file_path_or_buffer) as pdf:
                 # Check first page text to see if we should use coordinate parser?
                 # Always usage coordinate parser for this bank is better if layout matches.
                 # But we have multiple layouts.
                 # Let's try to extract with coords, if it yields transactions, return them.
                 transactions_coords, meta_coords = self._parse_with_coordinates(pdf)
                 if transactions_coords:
                     # Merge finding
                     metadata.update(meta_coords)
                     # If balance missing, maybe fallback or text scan?
                     # Ideally coords parser handles everything.
                     
                     # Check if we got balances in coords parser?
                     # If not, maybe run text scan for balances only?
                     # For now return what we have.
                     
                     # One edge case: Balances might be better extracted via regex on full text.
                     # Let's augment metadata with full text scan for balances if missing.
                     if not metadata['balance_start'] or not metadata['balance_end']:
                         full_text = ""
                         for page in pdf.pages:
                             full_text += (page.extract_text() or "") + "\n"
                         
                         meta_text = self._extract_metadata_text(full_text)
                         if not metadata['balance_start']: metadata['balance_start'] = meta_text.get('balance_start')
                         if not metadata['balance_end']: metadata['balance_end'] = meta_text.get('balance_end')
                         if not metadata['agency']: metadata['agency'] = meta_text.get('agency')
                         
                     return pd.DataFrame(transactions_coords), metadata
        except Exception as e:
            logger.error(f"Itau Coordinate Parser failed: {e}")
            # Fallback to text parser below
        
        return self._parse_text_fallback(file_path_or_buffer)

    def _parse_with_coordinates(self, pdf) -> tuple[list, dict]:
        transactions = []
        metadata = {}
        
        # Helper to group words into lines
        def get_lines(page):
            words = page.extract_words()
            words.sort(key=lambda w: (round(w['top']), w['x0']))
            lines = []
            if not words: return lines
            current_line = [words[0]]
            for w in words[1:]:
                # Same line if Y is close (within 3 pts)
                if abs(w['top'] - current_line[-1]['top']) < 3:
                    current_line.append(w)
                else:
                    lines.append(current_line)
                    current_line = [w]
            lines.append(current_line)
            return lines

        # Identify Columns based on X histogram or hardcoded from analysis
        # Analysis showed:
        # Date: X < 90
        # Lançamentos (Type): 90 <= X < 220
        # Razão Social (Name): 220 <= X < 360
        # CNPJ/CPF (Doc): 360 <= X < 470
        # Value: X >= 470
        
        for page in pdf.pages:
            lines = get_lines(page)
            
            # Buffer for "Lançamentos" line which might be above the Date line
            last_lancamento_desc = ""
            last_lancamento_y = 0
            
            for line_words in lines:
                # Get Y of line
                y = sum(w['top'] for w in line_words) / len(line_words)
                
                # Check for content in columns
                date_text = ""
                lanc_text = ""
                razao_text = ""
                doc_text = ""
                val_text = ""
                
                for w in line_words:
                    x = w['x0']
                    text = w['text']
                    
                    if x < 80:
                        date_text += text + " "
                    elif 80 <= x < 210:
                        lanc_text += text + " "
                    elif 210 <= x < 350:
                        razao_text += text + " "
                    elif 350 <= x < 460:
                        doc_text += text + " "
                    elif x >= 460:
                        val_text += text + " "
                
                date_text = date_text.strip()
                lanc_text = lanc_text.strip()
                razao_text = razao_text.strip()
                doc_text = doc_text.strip()
                val_text = val_text.strip()
                
                # Case 1: Header or Balance line
                if "SALDO ANTERIOR" in lanc_text.upper() or "SALDO ANTERIOR" in razao_text.upper():
                    # Extract balance
                     match_bal = re.search(r"([\d\.]+,\d{2})", val_text)
                     if match_bal:
                         val = self._parse_br_amount(match_bal.group(1))
                         if "(-)" in val_text or '-' in val_text: val = -abs(val)
                         metadata['balance_start'] = val
                    # continue # Do NOT continue, sometimes it is a transaction too? Usually not.
                
                # Case 2: Multi-line Transaction component (Lançamentos only)
                # If we have Lancamentos but NO Date and NO Value, precise storage
                if lanc_text and not date_text and not val_text:
                    last_lancamento_desc = lanc_text
                    last_lancamento_y = y
                    continue
                
                # Case 3: Transaction Row (Must have Date and Value)
                # Or just Date if value is on next line? (Rare in this layout)
                # In this layout, Date/Razao/Doc/Value are on one line.
                if re.match(r"\d{2}/\d{2}/\d{4}", date_text):
                     # Parse Date
                     try:
                         dt = datetime.strptime(date_text, "%d/%m/%Y").date()
                     except:
                         continue
                         
                     # Parse Value
                     if not val_text: continue # Must have value
                     try:
                        amount = self._parse_br_amount(val_text)
                     except:
                        continue
                     
                     # Check sign
                     # If validation fails, check keywords?
                     # Itaú PDF "columns" usually doesn't have D/C explicitly in value col?
                     # Actually in the sample `21,00` is positive but context is `PIX QR CODE RECEBIDO`.
                     # Wait, `PIX QR CODE RECEBIDO` -> Credit.
                     # `PAGAMENTO` -> Debit.
                     # Also visual position? X=489.
                     # In coordinates.txt: `612.3 493.0 3,50`.
                     # We need to rely on keywords for sign if there is no +/-.
                     
                     # Construct Description
                     # Merge with previous line if close (e.g. < 15 pts diff)
                     full_desc = ""
                     if last_lancamento_desc and abs(y - last_lancamento_y) < 20:
                         full_desc = f"{last_lancamento_desc} - "
                         last_lancamento_desc = "" # Consume it
                     
                     full_desc += razao_text
                     if lanc_text: full_desc += f" {lanc_text}" # If lancamento text on same line
                     if doc_text: full_desc += f" Doc:{doc_text}"
                     
                     # Heuristic Sign
                     # Defaults to negative for standard checking, positive for credits?
                     # Actually Itaú statement usually implies negative for standard list, simple amount.
                     # BUT `RECEBIDO` implies positive.
                     # `PAGAMENTO` implies negative.
                     
                     # Default to Negative (Expense) unless keyword says otherwise? 
                     # Or Default to Positive?
                     # In sample `PIX QR CODE RECEBIDO ... 21,00`. 21,00 is usually + in receipts but in statement?
                     # Let's assume unsigned = Debit, unless Credit keywords.
                     # Wait, usually bank statements use - sign for debits.
                     # If the sample `21,00` has NO minus, it might be Credit?
                     # Or maybe Itaú separates inputs and outputs?
                     # Let's look at `SALDO`.
                     # Row 40: `30/09 Saldo Anterior 0,00`.
                     # Row 49: `27/10 ... 21,00`.
                     # If it's `RECEBIDO`, it should be positive.
                     # If all are positive numbers, we MUST use keywords.
                     
                     if any(k in full_desc.upper() for k in ["RECEBIDO", "CRED", "RESGATE", "DEPOSITO", "TRANSF.CRED"]):
                         amount = abs(amount)
                     elif any(k in full_desc.upper() for k in ["PAGAMENTO", "ENVIO", "SAQUE", "TARIFA", "IOF", "SISPAG", "DÉBITO"]):
                         amount = -abs(amount)
                     else:
                         # Ambiguous. Default to negative if mostly payments?
                         # Safe bet: usually unsigned in simple columns implies Debit if not marked.
                         # But `PIX RECEBIDO` is definitely Credit.
                         # Let's check if there is a `-` text in Val column?
                         if "-" in val_text:
                             amount = -abs(amount)
                         else:
                             # If no sign and no keyword, assume Negative?
                             # In the sample `21,00` was `PIX RECEBIDO`.
                             # If I have `27,00` without keyword `RECEBIDO`?
                             # Let's look at coordinate sample.
                             # `THIAGO ... JUNIOR ... 27,00`. `PIX QR CODE RECEBIDO THIAGO`.
                             # All samples in that debug file seem to be `PIX QR CODE RECEBIDO`.
                             # So they are all Credits.
                             pass
                     
                     transactions.append({
                        'date': dt,
                        'amount': amount,
                        'description': full_desc.strip(),
                        'source': 'Bank'
                     })
                     
        return transactions, metadata

    def _extract_metadata_text(self, full_text):
        metadata = {}
        # Reuse existing regex logic
        period_match = re.search(r"período:?\s+(\d{2}/\d{2}/\d{4})\s+at[ée]\s+(\d{2}/\d{2}/\d{4})", full_text, re.IGNORECASE)
        if period_match:
             try:
                 metadata['start_date'] = datetime.strptime(period_match.group(1), "%d/%m/%Y").date()
                 metadata['end_date'] = datetime.strptime(period_match.group(2), "%d/%m/%Y").date()
             except: pass
             
        ag_match = re.search(r"Agência\s+(\d+)\s+Conta\s+([\d\-]+)", full_text, re.IGNORECASE)
        if ag_match:
            metadata['agency'] = ag_match.group(1)
            metadata['account'] = ag_match.group(2)
            
        header_bal_match = re.search(r"Saldo total.*?R\$\s*([\d\.]+,\d{2})", full_text, re.DOTALL | re.IGNORECASE)
        if header_bal_match:
             metadata['balance_end'] = self._parse_br_amount(header_bal_match.group(1)) # Check sign logic if needed
             
        return metadata



