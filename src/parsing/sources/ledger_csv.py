"""
Ledger CSV Parser

Parses accounting ledger CSV files exported from accounting systems.
"""
import logging
import pandas as pd
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)


class LedgerCSVParser(BaseParser):
    """
    Parser for accounting ledger CSV files.
    
    Handles Brazilian CSV format with proper sign detection based on Debit/Credit columns.
    """
    
    def parse(self, file_path_or_buffer):
        """
        Parse ledger CSV file with robust handling.
        
        Args:
            file_path_or_buffer: Path to CSV file or file-like object
            
        Returns:
            Tuple of (DataFrame, company_name) where DataFrame has columns: date, amount, description, source
        """
        # Use the corrected parsing logic from csv_helper
        from src.utils.csv_helper import _parse_ledger_csv
        
        try:
            df, company_name = _parse_ledger_csv(file_path_or_buffer)
            
            # Ensure output matches expected format
            # csv_helper returns: date, amount, description (and other numbered columns)
            # We need to ensure 'source' column exists
            if 'source' not in df.columns:
                df['source'] = 'Ledger'
            
            # Select only needed columns
            result_df = df[['date', 'amount', 'description', 'source']].copy()
            
            # Ensure date is datetime (csv_helper already does this)
            result_df['date'] = pd.to_datetime(result_df['date'])
            
            # Ensure amount is numeric (csv_helper already does this with sign)
            result_df['amount'] = pd.to_numeric(result_df['amount'], errors='coerce').fillna(0.0)
            
            return result_df, company_name
            
        except Exception as e:
            logger.error(f"Failed to parse ledger CSV: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame(), "Empresa"
