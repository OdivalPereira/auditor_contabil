"""
Base Classes for Parsing Module

Provides unified base classes for both:
- Parsers (for reconciliation - returns DataFrame)
- Extractors (for PDF conversion - returns Dict)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from src.common.logging_config import get_logger
import pandas as pd
import re
from datetime import datetime

logger = get_logger(__name__)


class BaseParser(ABC):
    """
    Abstract Base Class for all Parsers.
    Used primarily for reconciliation workflows.
    
    Returns:
        Tuple[DataFrame, Dict]: (transactions_df, metadata)
    """
    
    def parse_pdf(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        """
        Template method for processing a PDF file.
        Opens the PDF, iterates through pages, and collects transactions.
        """
        import pdfplumber
        all_txns = []
        bal_start = None
        bal_end = None
        
        try:
            with pdfplumber.open(file_path_or_buffer) as pdf:
                for i, page in enumerate(pdf.pages):
                    txns, b_s, b_e = self.extract_page(page)
                    all_txns.extend(txns)
                    
                    # Store the VERY FIRST balance found as bal_start
                    if bal_start is None and b_s is not None:
                        bal_start = b_s
                        logger.debug(f"Found bal_start: {bal_start}", page=i+1)
                        
                    if b_e is not None:
                        bal_end = b_e
                        logger.debug(f"Updated bal_end: {bal_end}", page=i+1)
        except Exception as e:
            logger.error(f"Parse Error in {self.__class__.__name__}: {e}", exc_info=True, parser=self.__class__.__name__)
            
        # Balance-Aware Deduplication
        deduped = []
        seen_keys = {}
        
        for tx in all_txns:
            desc_val = str(tx['description']).strip()
            balance_val = tx.get('balance', tx.get('bal_row'))
            key = (tx['date'], tx['amount'], balance_val, desc_val)
            
            if key in seen_keys:
                existing = seen_keys[key]
                if desc_val and desc_val not in existing['description']:
                    existing['description'] += " | " + desc_val
            else:
                seen_keys[key] = tx
                deduped.append(tx)
        
        # Add a unique sequence ID to each transaction within this file
        # to prevent them from being collapsed during consolidation if they are identical.
        for i, tx in enumerate(deduped):
            tx['internal_id'] = i

        df = pd.DataFrame(deduped)
        if not df.empty:
            df = df.drop_duplicates().reset_index(drop=True)
            
        metadata = {
            'bank': getattr(self, 'bank_name', 'Unknown Bank'),
            'balance_start': bal_start,
            'balance_end': bal_end
        }
        return df, metadata

    def extract_page(self, page) -> Tuple[list, float, float]:
        """
        Extracts transactions and balances from a single page.
        Defaults to extract_transactions_smart but can be overridden.
        """
        return self.extract_transactions_smart(page)
    
    def extract_transactions_smart(self, page_or_text) -> Tuple[list, float, float]:
        """
        Smart extraction that finds dates and values regardless of exact layout.
        Returns (transactions_list, first_balance_found, last_balance_found)
        """
        import pdfplumber
        if isinstance(page_or_text, str):
            return [], None, None

        # If it's a pdfplumber page
        words = page_or_text.extract_words()
        lines = {}
        for w in words:
            top = int(w['top'] // 2) * 2 # Group by 2px tolerance
            if top not in lines: lines[top] = []
            lines[top].append(w)
            
        txns = []
        desc_buffer = []
        bal_first = None
        bal_last = None
        
        amt_pattern = re.compile(r"(-?[\d\.]*,\d{2})\s*([CD])?")

        # Try to find a global year in the page
        full_page_text = page_or_text.extract_text() or ""
        global_year = None
        year_match = re.search(r"20\d{2}", full_page_text)
        if year_match: global_year = int(year_match.group(0))

        months_map = {
            'JAN': 1, 'FEV': 2, 'MAR': 3, 'ABR': 4, 'MAI': 5, 'JUN': 6,
            'JUL': 7, 'AGO': 8, 'SET': 9, 'OUT': 10, 'NOV': 11, 'DEZ': 12
        }

        for top in sorted(lines.keys()):
            line_words = sorted(lines[top], key=lambda x: x['x0'])
            text = " ".join([w['text'] for w in line_words])
            
            # Find all potential amounts on the line
            matches = list(amt_pattern.finditer(text))
            
            # Check for Balance markers
            is_balance_line = any(k in text.upper() for k in ["SALDO", "S A L D O", "TRANSPORTE"])
            is_start_bal = any(k in text.upper() for k in ["ANTERIOR", "INICIAL"])
            
            if is_balance_line and matches:
                val_s, dc = matches[-1].groups()
                bal_val = self._parse_br_amount(val_s)
                if dc == 'D': bal_val = -abs(bal_val)
                
                if bal_first is None or is_start_bal:
                    bal_first = bal_val
                bal_last = bal_val

            # Find Date (Supports DD/MM/YYYY, DD.MM.YYYY, DD/MM/YY, DD/MM or DD / MON)
            date_match = re.search(r"(\d{2})([/\.\s]+)([a-zA-Z]{3}|\d{2})(?:[/\.\s]+(\d{4}|\d{2}))?", text)
            
            if not date_match:
                if not self.should_ignore_line(text):
                    desc_buffer.append(text)
                continue
            
            # Found a date
            dt = None
            day, sep, mon_s, year_s = date_match.groups()
            
            try:
                # Handle numeric month vs name
                month = 1
                if mon_s.upper() in months_map:
                    month = months_map[mon_s.upper()]
                else:
                    month = int(mon_s)
                
                # Handle year
                year = global_year or datetime.now().year
                if year_s:
                    if len(year_s) == 2: year = 2000 + int(year_s)
                    else: year = int(year_s)
                
                dt = datetime(year, month, int(day)).date()
            except:
                # Fallback to simple regex if this custom one failed
                simple_match = re.search(r"(\d{2}[/\.]\d{2}[/\.](\d{4}|\d{2}))", text)
                if simple_match:
                    ds, ys = simple_match.groups()
                    try:
                        fmt = "%d/%m/%y" if len(ys)==2 else "%d/%m/%Y"
                        dt = datetime.strptime(ds.replace(".","/"), fmt).date()
                    except: pass
            
            if not dt:
                if not self.should_ignore_line(text):
                    desc_buffer.append(text)
                continue
            
            if len(matches) >= 1:
                # If we see 2+ numbers on a transaction line, usually last is balance
                if len(matches) >= 2:
                    pot_bal = self._parse_br_amount(matches[-1].group(1))
                    if bal_first is None: bal_first = pot_bal
                    bal_last = pot_bal
                    amt_match = matches[-2]
                else:
                    amt_match = matches[0]
                
                val_s, dc = amt_match.groups()
                amount = self._parse_br_amount(val_s)
                
                # Determine sign
                keywords_up = text.upper()
                if "-" in val_s or dc == 'D' or any(k in keywords_up for k in ['DEBITO', 'PAGTO', 'ENVIADO', 'SAQU', 'TARIFA', 'PIX -', 'PGTO', 'RESGATE']):
                    amount = -abs(amount)
                elif dc == 'C' or any(k in keywords_up for k in ['CREDITO', 'RECEBIDO', 'ESTORN', 'DEPOSITO', 'PIX +', 'APLICA']):
                    amount = abs(amount)
                
                if amount != 0:
                    description = " ".join(desc_buffer).strip()
                    if not description: description = text
                    txns.append({'date': dt, 'amount': amount, 'description': description, 'source': 'Bank'})
                    desc_buffer = []
            else:
                desc_buffer.append(text)
                
        if txns:
            logger.debug(f"Smart extraction found transactions.", count=len(txns), page_sample=full_page_text[:100] if 'full_page_text' in locals() else "N/A")
        return txns, bal_first, bal_last

    def should_ignore_line(self, line: str) -> bool:
        """
        Checks if a line should be ignored based on common keywords
        indicating balances, totals, or headers.
        """
        if not line:
            return True
            
        keywords = ["SALDO", "TOTAL", "ANTERIOR", "S A L D O", "TRANSPORTADO", "BLOQUEADO"]
        upper_line = line.upper()
        
        for k in keywords:
            if k in upper_line:
                return True

        # Check for explicitly zero amounts like "0,00" or "0.00" standing alone or at end
        # This is a heuristic. A better approach is to rely on parsed amount, but we are filtering LINES here.
        # If the line contains "0,00" or "0.00", it might be a zero value transaction or balance.
        # However, checking "0,00" might be risky if it appears in ID.
        # User requested: "ignorar o valor zero". Ideally this happens AFTER parsing the amount.
        # But if we want to filter the LINE, we look for 0,00 D or 0,00 C patterns often found in statements.
        
        # Regex for 0,00 value
        if re.search(r"\b0,00\s*[DC]?\b", line) or re.search(r"\b0\.00\s*[DC]?\b", line):
             return True
                
        return False

    @abstractmethod
    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        """
        Parses the PDF and returns a DataFrame of transactions and a metadata dict.
        Must be implemented by subclasses.
        """
        raise NotImplementedError
    
    def extract(self, file_path: str) -> dict:
        """
        Adapter method for ExtractorPipeline.
        Converts the (df, metadata) output of parse() into the dict format
        expected by the pipeline.
        """
        try:
            df, metadata = self.parse(file_path)
            
            transactions = []
            if not df.empty:
                # Ensure date is string for JSON compatibility if needed, 
                # but Pipeline uses UnifiedTransaction which handles dates.
                # Just converting to list of dicts.
                
                # Normalize columns if needed
                if 'description' in df.columns and 'memo' not in df.columns:
                    df['memo'] = df['description']
                
                transactions = df.to_dict(orient='records')
            
            return {
                'transactions': transactions,
                'account_info': metadata,
                'balance_info': {
                    'start': metadata.get('balance_start'),
                    'end': metadata.get('balance_end')
                }, 
                'validation': {'is_valid': True, 'msg': 'Parsed via Specialized Parser'},
                'discarded_candidates': []
            }
        except Exception as e:
            logger.error(f"Adapter extraction failed: {e}", exc_info=True)
            return {
                'transactions': [],
                'account_info': {},
                'error': str(e),
                'validation': {'is_valid': False, 'msg': str(e)}
            }

    def _parse_br_amount(self, amount_str) -> float:
        """
        Parses Brazilian Currency string to Absolute Float.
        Examples: 
            "1.000,00" -> 1000.0
            "-1.000,00" -> 1000.0
            "1000.00" -> 1000.0
        """
        if not amount_str:
            return 0.0
            
        # Check for already float-like/numeric
        if isinstance(amount_str, (float, int)):
             return abs(float(amount_str))
             
        clean_str = str(amount_str).replace('.', '').replace(',', '.')
        try:
            val = float(clean_str)
            return abs(val)  # ABSOLUTE VALUE ENFORCED
        except ValueError:
            return 0.0


class BaseExtractor(ABC):
    """
    Abstract Base Class for all PDF Extractors.
    Used primarily for PDF -> OFX conversion workflows.
    
    Returns:
        Dict with 'transactions', 'account_info', 'metadata'
    """
    
    @abstractmethod
    def identify(self, pdf_text: str) -> bool:
        """
        Returns True if this extractor can handle the given PDF text/metadata.
        """
        pass

    @abstractmethod
    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Main entry point. 
        Returns a dictionary containing:
        - 'transactions': List[Dict] or pd.DataFrame
        - 'account_info': Dict (bank_id, branch, acct)
        - 'metadata': Dict (date_range, etc)
        """
        pass
