import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

import re
from datetime import datetime

class SantanderPDFParser(BaseParser):
    bank_name = 'Santander'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        return self.parse_pdf(file_path_or_buffer)

    def extract_page(self, page):
        """
        Specialized extraction for Santander layouts.
        """
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        # 01/12/2025 Saldo do dia Cc + ContaMax principal R$ 4.376,19
        # Group 1: Date, Group 2: Name, Group 3: Balance
        bal_day_pattern = re.compile(r"(\d{2}/\d{2}/\d{4})\s+Saldo do dia\s+(.*?)\s+R\$\s+([\d\.,]+)")
        
        # 01/12/2025 Debito Aut. Fat.cartao Master Card FINAL 8668 - R$ 18,50
        # Group 1: Date, Group 2: Desc, Group 3: Sign, Group 4: Value
        txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+([+-])\s+R\$\s+([\d\.,]+)")

        for line in lines:
            line = line.strip()
            
            bm = bal_day_pattern.search(line)
            if bm:
                val = self._parse_br_amount(bm.group(3))
                if bal_start is None: bal_start = val
                bal_end = val
                continue
                
            tm = txn_pattern.search(line)
            if tm:
                dt_s, desc, sign, val_s = tm.groups()
                try:
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    amount = self._parse_br_amount(val_s)
                    if sign == '-': amount = -abs(amount)
                    
                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc.strip(),
                        'source': 'Bank'
                    })
                except: continue

        if not rows:
            return self.extract_transactions_smart(page)
            
        return rows, bal_start, bal_end
