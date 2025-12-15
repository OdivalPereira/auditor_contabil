
import logging
import pandas as pd
import pdfplumber
import re
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)

class StonePDFParser(BaseParser):
    """
    Parser for Stone monthly statement PDFs.
    
    Format: Text-based lines.
    Pattern: Date | Type (Opt) | Description | Amount | Balance
    Example: 31/01/2025 Débito Tarifa -0,70 4.006,49
    """

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        metadata = {
            'bank': 'Stone', 
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
            
            # Metadata extraction (Simple grep)
            ag_match = re.search(r"Agência\s+([\d\-]+)", full_text)
            cc_match = re.search(r"Conta\s+([\d\-]+)", full_text)
            
            if ag_match: metadata['agency'] = ag_match.group(1)
            if cc_match: metadata['account'] = cc_match.group(1)
            
            lines = full_text.split('\n')
            
            # Regex to capture transaction components
            # Group 1: Date (DD/MM/YYYY)
            # Group 2: Type (Optional: Crédito/Débito)
            # Group 3: Description (Greedy until amount)
            # Group 4: Amount (Signed, 2nd to last number)
            # Group 5: Balance (Last number)
            
            # Reformulate regex to handle both:
            # Type A (2025 samples): "30/06/2025 Crédito 37,26 13.407,59"
            # Type B (Legacy/Other): "31/07/25 Saída Tarifa - R$ 0,27 R$ 5.579,23"
            
            # Key differences in Type B:
            # - Date is DD/MM/YY
            # - Type is "Saída"/"Entrada" instead of "Débito"/"Crédito"
            # - Amounts have "R$" prefix
            # - Description might contain "-"
            
            # Unified Pattern Strategy:
            # 1. Date: ^(\d{2}/\d{2}/\d{2,4})
            # 2. Lazy content until Amount: (.*?)
            # 3. Amount: ([\-\sR$]*[\d\.]+,\d{2})  <-- Allow R$, space, minus
            # 4. Balance: ([\sR$]*[\d\.]+,\d{2})
            
            pattern = re.compile(
                r"^(\d{2}/\d{2}/\d{2,4})\s+(.*?)\s+((?:R\$\s*)?[\-\s]*[\d\.]+,\d{2})\s+((?:R\$\s*)?[\-\s]*[\d\.]+,\d{2})"
            )
            
            for line in lines:
                line = line.strip()
                if self.should_ignore_line(line):
                    continue
                
                match = pattern.search(line)
                if match:
                    date_str = match.group(1)
                    desc_raw = match.group(2).strip()
                    amount_str = match.group(3)
                    
                    # Cleanup Amount String
                    # Remove 'R$', spaces
                    amount_val = self._parse_br_amount(amount_str.replace("R$", "").replace(" ", ""))
                    
                    # Logic for sign in Type B:
                    # "Saída" or "Débito" usually means negative.
                    # But if amount_str already has "-", _parse_br_amount handles it today? 
                    # Let's check: "Saída ... - R$ 0,27". The "-" is captured in group 3?
                    # Regex group 3: ((?:R\$\s*)?[\-\s]*[\d\.]+,\d{2})
                    # Yes, it captures the minus if present.
                    
                    # Safety check on Description for direction if sign missing
                    # If "Saída" in desc or "Débito" in desc AND amount > 0:
                    #    amount = -amount
                    
                    if ("SAÍDA" in desc_raw.upper() or "DÉBITO" in desc_raw.upper()) and amount_val > 0:
                         amount_val = -amount_val
                    
                    if amount_val == 0.0: continue

                    try:
                        # Handle 2-digit year
                        if len(date_str) == 8: # DD/MM/YY
                            dt = datetime.strptime(date_str, "%d/%m/%y").date()
                        else:
                            dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                            
                        transactions.append({
                            'date': dt,
                            'amount': amount_val,
                            'description': desc_raw,
                            'source': 'Bank'
                        })
                    except ValueError:
                        continue
                        
        except Exception as e:
            logger.error(f"Error parsing Stone PDF: {e}")
            return pd.DataFrame(), {}

        df = pd.DataFrame(transactions)
        if not df.empty:
            metadata['start_date'] = df['date'].min()
            metadata['end_date'] = df['date'].max()
            
        return df, metadata
