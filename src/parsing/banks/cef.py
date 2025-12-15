import pdfplumber
import re
import logging
import pandas as pd
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)

class CEFPdfParser(BaseParser):
    """
    Parser for Caixa Econômica Federal (CEF) monthly statement PDFs.
    
    Format observed:
    Date | Doc Nr | Description | Value | Type (D/C) | Balance (Optional)
    """
    
    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        metadata = {
            'bank': 'Caixa Econômica Federal', 
            'agency': '', 
            'account': '', 
            'start_date': None, 
            'end_date': None
        }
        transactions = []
        
        full_text = ""
        try:
            with pdfplumber.open(file_path_or_buffer) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception as e:
            logger.error(f"Error reading PDF with pdfplumber: {e}")
            return pd.DataFrame(), {}
            
        # Extract Metadata (Header)
        # Typical header: "Agência: 1234" ... "Conta: 1234.001.00000000-0"
        ag_match = re.search(r"Agência[:\s]*(\d+)", full_text, re.IGNORECASE)
        cc_match = re.search(r"Conta[:\s]*([\d\.\-]+)", full_text, re.IGNORECASE)
        
        if ag_match:
            metadata['agency'] = ag_match.group(1)
        if cc_match:
            metadata['account'] = cc_match.group(1)
            
        lines = full_text.split('\n')
        
        # Regex Pattern
        # 30/04/2025 000000 CRED TED 1.824,34 C 1.824,34 C
        # Groups: Date, Doc, Desc, Value, Type
        pattern = re.compile(
            r"^(\d{2}/\d{2}/\d{4})\s+"       # Date
            r"(\d+)\s+"                      # Doc Number (digits)
            r"(.+?)\s+"                      # Description (Lazy)
            r"([\d\.]+,\d{2})\s+"            # Value
            r"([DC])"                        # Type
        )
        
        for line in lines:
            line = line.strip()
            if self.should_ignore_line(line):
                continue
            
            # Explicitly skip balance/summary lines
            if "SALDO" in line.upper() or "TOTAL" in line.upper():
                continue
            
            match = pattern.match(line)
            if match:
                date_str = match.group(1)
                doc_num = match.group(2)
                desc = match.group(3).strip()
                val_str = match.group(4)
                dc_type = match.group(5)
                
                amount = self._parse_br_amount(val_str)
                if dc_type == 'D':
                    amount = -abs(amount)
                else:
                    amount = abs(amount)
                    
                full_desc = f"{desc} Doc:{doc_num}"
                
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                    transactions.append({
                        'date': dt,
                        'amount': amount,
                        'description': full_desc,
                        'source': 'Bank'
                    })
                except ValueError:
                    continue
                    
        df = pd.DataFrame(transactions)
        if not df.empty:
            metadata['start_date'] = df['date'].min()
            metadata['end_date'] = df['date'].max()
            
        return df, metadata
