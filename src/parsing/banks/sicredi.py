import pdfplumber
import re
import logging
import pandas as pd
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)

class SicrediPDFParser(BaseParser):
    """
    Parser for Sicredi monthly statement PDFs.
    
    Supports two observed layouts:
    1. Columns Layout: Separate 'DEBITO' and 'CREDITO' columns.
    2. Signed Layout: Single 'VALOR' column with signed amounts (-,+).
    """

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        metadata = {
            'bank': 'Sicredi', 
            'agency': '', 
            'account': '', 
            'start_date': None, 
            'end_date': None
        }
        
        try:
            with pdfplumber.open(file_path_or_buffer) as pdf:
                # 1. Detect Strategy based on Page 1 headers
                first_page = pdf.pages[0]
                text = first_page.extract_text() or ""
                
                strategy = "UNKNOWN"
                if "DEBITO" in text and "CREDITO" in text:
                    strategy = "COLUMNS"
                elif "DATA" in text and "Documento" in text:
                     # Fallback / Default
                    strategy = "SIGNED"
                else:
                    strategy = "SIGNED" # Default
                    
                logger.info(f"Sicredi Parser: Detected strategy '{strategy}'")
                
                # 2. Extract Words & Parse
                all_txns = []
                for page in pdf.pages:
                    words = page.extract_words()
                    if strategy == "COLUMNS":
                        page_txns = self._parse_columns(words)
                    else:
                        page_txns = self._parse_signed(words)
                        
                    all_txns.extend(page_txns)
                
                # Metadata extraction (naive check on text)
                # Need to refine if specific metadata needed, but strict txn extraction is priority
                pass 

        except Exception as e:
            logger.error(f"Error reading PDF with pdfplumber: {e}")
            return pd.DataFrame(), {}

        df = pd.DataFrame(all_txns)
        if not df.empty:
            metadata['start_date'] = df['date'].min()
            metadata['end_date'] = df['date'].max()
            
        return df, metadata

    def _parse_columns(self, words) -> list:
        """
        Parses layout with distinct DEBITO and CREDITO columns.
        X-Ranges (Approx from debug):
        - Debit: 370 - 410
        - Credit: 440 - 490
        - Balance: > 520 (Ignored)
        """
        transactions = []
        
        # Group by line (top)
        lines = {}
        for w in words:
            top = int(w['top'])
            if top not in lines: lines[top] = []
            lines[top].append(w)
            
        sorted_tops = sorted(lines.keys())
        
        for top in sorted_tops:
            line_words = lines[top]
            line_words.sort(key=lambda x: x['x0'])
            
            # Reconstruct text for filtering
            full_line_text = " ".join([w['text'] for w in line_words])
            if self.should_ignore_line(full_line_text):
                continue
                
            # Date Check
            first_word = line_words[0]
            if not re.match(r"^\d{2}/\d{2}/\d{4}", first_word['text']):
                continue
                
            date_str = first_word['text']
            
            # Find Amounts in specific columns
            amount = 0.0
            found_amt = False
            
            # Identify Description words (everything before the amount column)
            desc_words = []
            
            for w in line_words[1:]:
                cw = w['text']
                cx0 = float(w['x0'])
                
                # Check Debit Column
                if 360 < cx0 < 415:
                    # Is this a number?
                    val = self._parse_br_amount(cw)
                    if val != 0 or "0,00" in cw: 
                         amount = -abs(val)
                         found_amt = True
                         continue # Don't add to description
                
                # Check Credit Column
                if 440 < cx0 < 495:
                    val = self._parse_br_amount(cw)
                    if val != 0 or "0,00" in cw:
                        amount = abs(val)
                        found_amt = True
                        continue

                # If x is way over to right, it's balance, skip
                if cx0 > 510:
                    continue
                    
                # Otherwise, description
                if not found_amt:
                    desc_words.append(cw)
            
            if found_amt:
                 # Filter zero amounts again (though should_ignore_line catches strict 0,00)
                 # self._parse_br_amount already returns 0.0 if fail
                 if amount == 0.0: continue

                 try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                    description = " ".join(desc_words)
                    transactions.append({
                        'date': dt,
                        'amount': amount,
                        'description': description,
                        'source': 'Bank'
                    })
                 except ValueError:
                    continue

        return transactions

    def _parse_signed(self, words) -> list:
        """
        Parses layout with single VALOR column (signed).
        X-Ranges:
        - Amount: ~440 - 500
        - Balance: ~500+ (often rightmost)
        """
        transactions = []
        
        lines = {}
        for w in words:
            top = int(w['top'])
            if top not in lines: lines[top] = []
            lines[top].append(w)
            
        sorted_tops = sorted(lines.keys())
        
        for top in sorted_tops:
            line_words = lines[top]
            line_words.sort(key=lambda x: x['x0'])
            
            full_line_text = " ".join([w['text'] for w in line_words])
            if self.should_ignore_line(full_line_text):
                continue
            
            first_word = line_words[0]
            if not re.match(r"^\d{2}/\d{2}", first_word['text']): # Sometimes DD/MM in this layout? 
                # Actually debug showed DD/MM/YYYY in extracted words usually
                # "01/08/2025"
                continue
            
            date_str = first_word['text']
            # Normalization for date
            if len(date_str) == 5: # DD/MM
                # Assume current year? Or try to find year in header metadata?
                # For now fail safe, skip or append placeholder year
                # But debug showed 2025 in all files
                pass
            
            # Find numbers starting from end
            # We expect [Desc] [Amount] [Balance?]
            # Iterate backwards
            
            amount = 0.0
            found_amt = False
            desc_words = []
            
            # Identify potential number candidates
            # Heuristic: Find all words that look like numbers
            number_indices = []
            for idx, w in enumerate(line_words):
                if idx == 0: continue # Skip date
                if re.search(r"[\d]+,\d{2}", w['text']):
                     number_indices.append(idx)
            
            if not number_indices:
                continue
                
            # Logic:
            # If 2 numbers: Left is Amount, Right is Balance.
            # If 1 number:
            #    Check coordinates.
            #    Amount is known to be around x=440-490
            #    Balance is around x=500+
            
            amt_idx = -1
            
            if len(number_indices) >= 2:
                # Assume second to last is Amount, last is Balance
                # Wait, verify coordinates
                # Ex: -100,00 (x448)  5.682 (x492). 
                # Yes, 2nd to last number word is Amount.
                amt_idx = number_indices[-2]
            elif len(number_indices) == 1:
                # Is it amount or balance?
                # Check coordinate
                w = line_words[number_indices[0]]
                cx0 = float(w['x0'])
                # Debug: Amount x0 ~ 440-466. Balance x0 ~ 513+.
                # Threshold: 500
                if cx0 < 500:
                    amt_idx = number_indices[0]
                else:
                    # It's probably just a balance line carried over?
                    continue
            
            if amt_idx != -1:
                amt_word = line_words[amt_idx]
                val_str = amt_word['text']
                
                # Check minus sign
                is_negative = "-" in val_str or "(" in val_str
                val = self._parse_br_amount(val_str)
                
                if is_negative:
                    amount = -abs(val)
                else:
                    # If layout is strictly signed, positives are credits
                    amount = abs(val)
                
                if amount == 0.0: continue
                
                # Description: All words between Date and Amount
                # Note: line_words[1 : amt_idx]
                desc_slice = line_words[1:amt_idx]
                description = " ".join([w['text'] for w in desc_slice])
                
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                    transactions.append({
                        'date': dt,
                        'amount': amount,
                        'description': description,
                        'source': 'Bank'
                    })
                except ValueError:
                    continue

        return transactions
