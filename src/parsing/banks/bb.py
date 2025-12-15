import pdfplumber
import re
import logging
import pandas as pd
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)


class BBPdfParser(BaseParser):
    """
    Parser for Banco do Brasil receipt PDFs (comprovantes).
    
    Format: Value | Sign | Date | Description
    Example: 1.000,00 (+) 15/05/2025 Transferencia
    """
    
    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        # Handle file pointer or path
        is_path = isinstance(file_path_or_buffer, (str, bytes))
        
        transactions = []
        metadata = {
            'bank': 'Banco do Brasil', 
            'agency': '', 
            'account': '', 
            'start_date': None, 
            'end_date': None
        }
        
        # Regex: Value | Sign | Date | Description
        txn_pattern = re.compile(r"^([\d\.]+,\d{2})\s*(\(\+\)|\(\-\))(\d{2}/\d{2}/\d{3,4})\s*(.*)")
        
        full_text = ""
        try:
            # pdfplumber requires a path or file-like object
            with pdfplumber.open(file_path_or_buffer) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
        except Exception as e:
            logger.error(f"Error reading PDF with pdfplumber: {e}")
            return pd.DataFrame(), metadata
        
        # Extract Metadata
        ag_match = re.search(r"Agência[:\s]*([\d\-X]+)", full_text, re.IGNORECASE)
        cc_match = re.search(r"Conta.*[:\s]*([\d\-X]+)", full_text, re.IGNORECASE)
        
        if ag_match: 
            metadata['agency'] = ag_match.group(1)
        if cc_match: 
            metadata['account'] = cc_match.group(1)

        lines = full_text.split('\n')
        for line in lines:
            line = line.strip()
            if self.should_ignore_line(line):
                continue
                
            match = txn_pattern.match(line)
            if match:
                val_str = match.group(1)
                sign_str = match.group(2)
                date_str = match.group(3)
                rest = match.group(4)
                
                amount = self._parse_br_amount(val_str)
                
                # Fix truncated date
                if len(date_str) == 9:
                    date_str += "5"
                    
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                    transactions.append({
                        'date': dt,
                        'amount': amount,
                        'description': rest,
                        'source': 'Bank'
                    })
                except ValueError:
                    continue
        
        df = pd.DataFrame(transactions)
        if not df.empty:
            metadata['start_date'] = df['date'].min()
            metadata['end_date'] = df['date'].max()
            
        return df, metadata


class BBMonthlyPDFParser(BaseParser):
    """
    Parser for Banco do Brasil monthly statement PDFs.
    
    Format: Date | Description | Value | Type (C/D)
    Example: 02/01/2025 Pagamento de Boleto 782,38 D
    """
    
    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        """
        Attempts to parse the PDF using multiple strategies.
        """
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
        
        # Strategy 1: Tabular Layout (2025 style)
        # Columns: Date | Ag | Lote | Hist | Desc | Doc | Value | Type | Balance
        df_tab, meta_tab = self._parse_tabular_2025(full_text)
        if not df_tab.empty:
            return df_tab, meta_tab
            
        # Strategy 2: Legacy Layout
        df_leg, meta_leg = self._parse_legacy(full_text)
        return df_leg, meta_leg

    def _parse_tabular_2025(self, text: str) -> tuple[pd.DataFrame, dict]:
        metadata = self._extract_common_metadata(text)
        transactions = []
        
        # Regex: Date | Ag/Lote/Hist (Variable/Merged) | Description (Lazy) | Doc (No spaces) | Value | Type
        # Adjusted to handle merged numbers between Date and Description
        pattern = re.compile(
            r"^(\d{2}/\d{2}/\d{4})\s+"        # Date
            r"[\d\s\-X]+?\s+"                 # Junk numbers (Ag/Lote/Hist) - Non-greedy, eats spaces
            r"(.+?)\s+"                       # Description (Lazy)
            r"([^\s]+)\s+"                    # Document (No spaces)
            r"([\d\.]+,\d{2})\s+"             # Value
            r"([DC])"                         # Type
        )
        
        # Global Balance Extraction (Backup)
        # BB: "S A L D O" usually at the end with a value
        if 'balance_end' not in metadata:
            end_match = re.search(r"(?:S\s*A\s*L\s*D\s*O|Saldo)\s+([\d\.]+,\d{2})\s*([DC])", text)
            if end_match:
                 val = self._parse_br_amount(end_match.group(1))
                 if end_match.group(2) == 'D': val = -val
                 metadata['balance_end'] = val
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            
            # Check for Balance Lines (Before ignore check)
            if "SALDO ANTERIOR" in line.upper():
                 match_bal = re.search(r"([\d\.]+,\d{2})\s*([DC])", line)
                 if match_bal:
                     val = self._parse_br_amount(match_bal.group(1))
                     if match_bal.group(2) == 'D': val = -val
                     metadata['balance_start'] = val
            
            if "S A L D O" in line.upper().replace(" ", ""): 
                 match_bal = re.search(r"([\d\.]+,\d{2})\s*([DC])", line)
                 if match_bal:
                     val = self._parse_br_amount(match_bal.group(1))
                     if match_bal.group(2) == 'D': val = -val
                     metadata['balance_end'] = val

            if self.should_ignore_line(line):
                continue
                
            match = pattern.match(line)
            if match:
                date_str = match.group(1)
                desc = match.group(2).strip()
                doc_num = match.group(3)
                val_str = match.group(4)
                dc_type = match.group(5)
                
                # Attempt repair if Document and Value are merged in the source text
                # (Though specific regex above might separate them if space exists, 
                # often pypdf merges them if close. 
                # If regex matched, they are separated by space. 
                # If NOT matched, we might need a backup regex for merged Doc+Value?
                # Actually, if Doc+Value are merged, the above regex `([^\s]+)\s+([\d\.]+,\d{2})` 
                # consumes the merged blob into `doc_num` and fails to match `val_str`.
                # We need a fallback or a smarter regex.)
                pass
            else:
                # Fallback for merged Doc+Value
                # Pattern: Date ... Desc ... DocValue Type
                # We can try to repair lines that look like transactions but failed the strict Split check
                # But for now let's trust the repair is needed on the extracted values?
                # No, if regex fails, we don't get values.
                
                # Let's try an alternative pattern for Merged Doc+Value
                match_merged = re.match(
                    r"^(\d{2}/\d{2}/\d{4})\s+[\d\s\-X]+?\s+(.+?)\s+([^\s]+)\s+([DC])", 
                    line
                )
                if match_merged:
                    # The `[^\s]+` (group 3) captured "Doc+Value"
                    date_str = match_merged.group(1)
                    desc = match_merged.group(2).strip()
                    doc_val_merged = match_merged.group(3)
                    dc_type = match_merged.group(4)
                    
                    # Split Doc and Value
                    # Value format: 1.256,68 (ends with ,DD)
                    # Doc: 553.426.000.019.913
                    # Combined: 553.426.000.019.9131.256,68
                    # Heuristic: Find last comma. Take 2 digits after it.
                    last_comma = doc_val_merged.rfind(',')
                    if last_comma != -1 and last_comma + 3 <= len(doc_val_merged):
                        val_str = doc_val_merged[last_comma - 100 : last_comma + 3] # generous slice
                        # Refine value extraction from suffix
                        # Clean points matches from right
                        # Actually simpler: standard Brazilian formatting validation
                        # We can walk backwards from end
                        pass
                        # For now, let's just reuse the _repair_merged_id logic which was designed for specific case
                        # Or rewrite it.
                        
                        # Let's try a regex search for value at end of the string
                        val_match = re.search(r"([\d\.]+,\d{2})$", doc_val_merged)
                        if val_match:
                            val_str = val_match.group(1)
                            doc_num = doc_val_merged[:val_match.start()]
                        else:
                            continue 
                    else:
                        continue
                else:
                    continue

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

    def _parse_legacy(self, text: str) -> tuple[pd.DataFrame, dict]:
        metadata = self._extract_common_metadata(text)
        transactions = []
        
        lines = text.split('\n')
        # Regex for BB Monthly: Date | Description (greedy) | Value | Type
        txn_pattern = re.compile(
            r"^(\d{2}/\d{2}/\d{4})\s+(.+?)(\d{1,3}(?:\.\d{3})*,\d{2})\s+([CD])"
        )
        
        for line in lines:
            line = line.strip()
            if self.should_ignore_line(line):
                # Even if ignored as transaction, check for balance?
                # Actually, should_ignore_line returns True for "SALDO" keywords.
                # So we MUST check for balance BEFORE ignore check or modify ignore check.
                # But here we are inside loop.
                # Let's check balance first.
                pass
            
            # Check for Balance Lines
            # Start: "Saldo Anterior"
            if "SALDO ANTERIOR" in line.upper():
                 # Try to extract the numeric value
                 match_bal = re.search(r"([\d\.]+,\d{2})\s*([DC])", line)
                 if match_bal:
                     val = self._parse_br_amount(match_bal.group(1))
                     if match_bal.group(2) == 'D': val = -val
                     metadata['balance_start'] = val
                     
            # End: "S A L D O" (often spaced)
            if "S A L D O" in line.upper().replace(" ", ""): 
                 match_bal = re.search(r"([\d\.]+,\d{2})\s*([DC])", line)
                 if match_bal:
                     val = self._parse_br_amount(match_bal.group(1))
                     if match_bal.group(2) == 'D': val = -val
                     metadata['balance_end'] = val

            if self.should_ignore_line(line):
                continue


            match = txn_pattern.match(line)
            if match:
                date_str = match.group(1)
                desc = match.group(2).strip()
                val_str = match.group(3)
                dc_type = match.group(4)
                
                # Heuristic repair for merged ID/amount
                desc, val_str = self._repair_merged_id(desc, val_str)
                
                amount = self._parse_br_amount(val_str)
                if dc_type == 'D':
                    amount = -abs(amount)
                else:
                    amount = abs(amount)
                    
                try:
                    dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                    transactions.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc,
                        'source': 'Bank'
                    })
                except ValueError:
                    continue
                    
        df = pd.DataFrame(transactions)
        if not df.empty:
            metadata['start_date'] = df['date'].min()
            metadata['end_date'] = df['date'].max()
            
        return df, metadata
        
    def _extract_common_metadata(self, text: str) -> dict:
        metadata = {
            'bank': 'Banco do Brasil', 
            'agency': '', 
            'account': '', 
            'start_date': None, 
            'end_date': None
        }
        ag_match = re.search(r"Agência[:\s]+([\d\-X]+)", text, re.IGNORECASE)
        cc_match = re.search(r"Conta.*[:\s]+([\d\-X]+)", text, re.IGNORECASE)
        
        if ag_match: 
            metadata['agency'] = ag_match.group(1)
        if cc_match: 
            metadata['account'] = cc_match.group(1)
            
        return metadata
    
    def _repair_merged_id(self, desc: str, val_str: str) -> tuple[str, str]:
        """
        Repairs cases where ID digits merge with amount.
        
        Example: "...132.1" + "616.766,70" should become "...132.161" + "6.766,70"
        """
        last_dot_idx = desc.rfind('.')
        if last_dot_idx != -1 and last_dot_idx > len(desc) - 5:
            suffix = desc[last_dot_idx + 1:]
            if suffix.isdigit() and len(suffix) < 3:
                missing_count = 3 - len(suffix)
                candidate_digits = val_str.replace('.', '')[:missing_count]
                
                if len(candidate_digits) == missing_count and candidate_digits.isdigit():
                    potential_digits = val_str[:missing_count]
                    if potential_digits == candidate_digits:
                        new_desc = desc + potential_digits
                        new_val_str = val_str[missing_count:]
                        return new_desc, new_val_str
        
        return desc, val_str
