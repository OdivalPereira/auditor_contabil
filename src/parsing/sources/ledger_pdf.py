"""
Ledger PDF Parser

Parses accounting ledger PDFs with balance-based transaction detection.
"""
import re
import logging
import pandas as pd
from pypdf import PdfReader
from decimal import Decimal
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)


class LedgerParser(BaseParser):
    """
    Parser for accounting ledger PDF files.
    
    Uses balance difference method to calculate transaction amounts
    from running balance columns.
    """
    
    def parse(self, file_path_or_buffer) -> pd.DataFrame:
        # Delegate CSV files to CSV parser
        if isinstance(file_path_or_buffer, str) and file_path_or_buffer.lower().endswith('.csv'):
            from .ledger_csv import LedgerCSVParser
            return LedgerCSVParser().parse(file_path_or_buffer)
        
        if hasattr(file_path_or_buffer, 'name') and file_path_or_buffer.name.lower().endswith('.csv'):
            from .ledger_csv import LedgerCSVParser
            return LedgerCSVParser().parse(file_path_or_buffer)
              
        reader = PdfReader(file_path_or_buffer)
        transactions = []
        
        current_date = None
        prev_balance = Decimal("0.00") 
        
        date_pattern = re.compile(r"^(\d{2}/\d{2}/\d{4})$")
        
        full_text_lines = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text_lines.extend(text.split('\n'))
                
        i = 0
        while i < len(full_text_lines):
            line = full_text_lines[i].strip()
            
            # Skip header/footer lines
            if "Total" in line or "Saldo anterior" in line or "TRANSPORTE" in line:
                i += 1
                continue

            date_match = date_pattern.match(line)
            if date_match:
                current_date = datetime.strptime(date_match.group(1), "%d/%m/%Y").date()
                i += 1
                continue
                
            # Try to extract starting balance of the line
            balance_match = re.match(r"^([\d\.]+,\d{2})([DC])", line)
            
            final_amount = None
            desc = ""
            
            if balance_match:
                bal_val_str = balance_match.group(1)
                dc = balance_match.group(2)
                
                # Parse current balance
                if dc == 'D':
                    current_balance_val = self._parse_br_amount(bal_val_str)
                else: 
                    current_balance_val = -self._parse_br_amount(bal_val_str)
                
                # Calculate transaction value from balance difference
                final_amount = abs(current_balance_val - prev_balance)
                
                # Cleanup description
                clean_line = line[len(balance_match.group(0)):]
                desc = clean_line.strip()
                
                transactions.append({
                    'date': current_date,
                    'amount': float(final_amount),
                    'description': desc,
                    'source': 'Ledger'
                })
                
                prev_balance = current_balance_val
            
            else:
                # Continuation line - append to previous description
                if transactions:
                    transactions[-1]['description'] += " " + line.strip()

            i += 1
            
        return pd.DataFrame(transactions)
