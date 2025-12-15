"""
Base Classes for Parsing Module

Provides unified base classes for both:
- Parsers (for reconciliation - returns DataFrame)
- Extractors (for PDF conversion - returns Dict)
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import logging
import pandas as pd
import re

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract Base Class for all Parsers.
    Used primarily for reconciliation workflows.
    
    Returns:
        Tuple[DataFrame, Dict]: (transactions_df, metadata)
    """
    
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
