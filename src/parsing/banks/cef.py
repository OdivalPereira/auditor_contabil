import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

import re
from datetime import datetime

class CEFPdfParser(BaseParser):
    bank_name = 'CEF'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        return self.parse_pdf(file_path_or_buffer)

    def extract_page(self, page):
        """
        Specialized extraction for CEF layouts.
        """
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        # Regex for CEF transaction lines
        # Example: '02/01/2025 000000 PREST EMP 4.401,24 D 3.005,78 D'
        # Group 1: Date, Group 2: Doc, Group 3: Memo, Group 4: Value, Group 5: VSign, Group 6: Bal, Group 7: BSign
        txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(\d+)\s+(.*?)\s+([\d\.,]+)\s+([CD])\s+([\d\.,]+)\s+([CD])")
        
        # Balance Anterior detection
        # Example: '000000 SALDO ANTERIOR 0,00 1.395,46 C'
        start_bal_pattern = re.compile(r"000000\s+SALDO ANTERIOR\s+([\d\.,]+)\s+([\d\.,]+)\s+([CD])")

        for line in lines:
            line = line.strip()
            
            # Check for starting balance
            sb_match = start_bal_pattern.search(line)
            if sb_match:
                val = self._parse_br_amount(sb_match.group(2))
                if sb_match.group(3) == 'D': val = -abs(val)
                if bal_start is None: bal_start = val
                continue
                
            # Check for transactions
            m = txn_pattern.search(line)
            if m:
                dt_s, doc, desc, val_s, v_sign, bal_s, b_sign = m.groups()
                try:
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    amount = self._parse_br_amount(val_s)
                    if v_sign == 'D': amount = -abs(amount)
                    
                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc.strip(),
                        'doc': doc,
                        'source': 'Bank'
                    })
                    
                    bal_val = self._parse_br_amount(bal_s)
                    if b_sign == 'D': bal_val = -abs(bal_val)
                    bal_end = bal_val
                except: continue

        if not rows:
            return self.extract_transactions_smart(page)
            
        return rows, bal_start, bal_end
