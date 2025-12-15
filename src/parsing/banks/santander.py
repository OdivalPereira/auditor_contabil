import pdfplumber
import re
import logging
import pandas as pd
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)

class SantanderPDFParser(BaseParser):
    """
    Parser for Santander monthly statement PDFs.
    
    Layout:
    - Tabular format with signed amounts.
    - Amount column ends approximately between x=470 and x=505.
    - Balance column follows to the right.
    """

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        metadata = {
            'bank': 'Santander', 
            'agency': '', 
            'account': '', 
            'start_date': None, 
            'end_date': None
        }
        
        all_txns = []
        
        try:
            with pdfplumber.open(file_path_or_buffer) as pdf:
                for page in pdf.pages:
                    words = page.extract_words()
                    page_txns = self._parse_page_words(words)
                    all_txns.extend(page_txns)

        except Exception as e:
            logger.error(f"Error reading PDF with pdfplumber: {e}")
            return pd.DataFrame(), {}

        df = pd.DataFrame(all_txns)
        if not df.empty:
            metadata['start_date'] = df['date'].min()
            metadata['end_date'] = df['date'].max()
            
        return df, metadata

    def _parse_page_words(self, words) -> list:
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
            
            full_line_text = " ".join([w['text'] for w in line_words])
            if self.should_ignore_line(full_line_text):
                continue
            
            first_word = line_words[0]
            # Match Date DD/MM/YYYY
            # Note: Santander sometimes only has DD/MM in body?
            # Debug showed: "01/12/2025" or "06/06/2024". So Full Date is common.
            # But sometimes extraction might split it?
            
            date_str = first_word['text']
            if not re.match(r"^\d{2}/\d{2}/\d{4}", date_str):
                 continue
                 
            # Find Amount
            # Logic: Amount matches regex number pattern AND matches X-Coordinate range
            # Range: 470 < x1 < 505
            
            amount = 0.0
            found_amt_idx = -1
            
            for idx, w in enumerate(line_words):
                if idx == 0: continue # Skip date
                
                cx1 = float(w['x1'])
                if 465 < cx1 < 510: # Allow slight buffer around 470-505
                     # Check if looks like amount
                     text_val = w['text']
                     # Must have digits and comma/dot
                     if re.search(r"\d", text_val) and ("," in text_val or "." in text_val):
                         val = self._parse_br_amount(text_val)
                         # Explicit check for sign in text
                         # _parse_br_amount handles it but let's be sure about logic
                         if "-" in text_val:
                             amount = -abs(val)
                         else:
                             amount = abs(val) # Santander signed: positive is credit, negative is debit
                         
                         found_amt_idx = idx
                         break # Found the amount, stop looking
            
            if found_amt_idx != -1:
                 # Check filter again for zero
                 if amount == 0.0: continue
                 
                 # Description is everything between Date and Amount
                 desc_slice = line_words[1:found_amt_idx]
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
