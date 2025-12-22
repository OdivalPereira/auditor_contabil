import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

import re
from datetime import datetime

class StonePDFParser(BaseParser):
    bank_name = 'Stone'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        df, metadata = self.parse_pdf(file_path_or_buffer)
        
        # Stone is Descending (newest first). 
        # Swap start/end balances and reverse rows for standard reconciliation.
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)
            
            # Swap balances
            old_start = metadata.get('balance_start')  # This is from FIRST page (31/05 = end)
            old_end = metadata.get('balance_end')  # This is from LAST page (01/05 = after first txn)
            
            # IMPORTANT: old_end is the balance AFTER the first (oldest) transaction
            # To get the true starting balance, we need to reverse that transaction
            first_txn_amount = df.iloc[0]['amount']  # First transaction in chronological order
            true_start = old_end - first_txn_amount  # Reverse the transaction
            
            metadata['balance_start'] = true_start
            metadata['balance_end'] = old_start
            
        return df, metadata

    def extract_page(self, page):
        """
        Specialized extraction for Stone layouts.
        Handles multi-line descriptions where:
        Line 1: DATE TYPE DESCRIPTION AMOUNT BALANCE
        Line 2: Additional description (e.g., "Pix | Maquininha")
        """
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        # Pattern: 31/05/25 Saída Tarifa - R$ 0,44 R$ 2.313,21
        # Pattern: 31/05/25 Entrada NOME R$ 59,00 R$ 2.313,21
        txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{2})\s+(Entrada|Saída)\s*(.*?)\s*(-?)\s*R\$\s*([\d\.,]+)\s+(-?)\s*R\$\s*([\d\.,]+)")
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            m = txn_pattern.search(line)
            if m:
                dt_s, ttype, desc, v_sign, val_s, b_sign, bal_s = m.groups()
                try:
                    dt = datetime.strptime(dt_s, "%d/%m/%y").date()
                    amount = self._parse_br_amount(val_s)
                    if v_sign == '-' or ttype.upper() == 'SAÍDA' or ttype.upper() == 'SAIDA':
                        amount = -abs(amount)
                    else:
                        amount = abs(amount)
                    
                    # Build full description from current line
                    full_desc = desc.strip() or ttype
                    
                    # Check if next line is a continuation (doesn't start with date)
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        # If next line doesn't start with a date pattern, it's a continuation
                        if next_line and not re.match(r'^\d{2}/\d{2}/\d{2}\s', next_line):
                            # Skip common headers
                            if next_line not in ['DATA', 'TIPO', 'DESCRIÇÃO', 'VALOR', 'SALDO', 'CONTRAPARTE']:
                                full_desc = (full_desc + " " + next_line).strip()
                                i += 1  # Skip the continuation line
                    
                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': full_desc,
                        'source': 'Bank'
                    })
                    
                    bal_val = self._parse_br_amount(bal_s)
                    if b_sign == '-': bal_val = -abs(bal_val)
                    
                    if bal_start is None: bal_start = bal_val
                    bal_end = bal_val
                except: 
                    pass
            
            i += 1

        if not rows:
            return self.extract_transactions_smart(page)
            
        return rows, bal_start, bal_end
