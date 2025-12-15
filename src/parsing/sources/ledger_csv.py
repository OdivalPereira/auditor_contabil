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
    
    Handles Brazilian CSV format with semicolon separator and Latin1 encoding.
    Expected columns: Data, Valor, Débito, Crédito, Complemento
    """
    
    def parse(self, file_path_or_buffer) -> pd.DataFrame:
        """
        Parse ledger CSV file.
        
        Args:
            file_path_or_buffer: Path to CSV file or file-like object
            
        Returns:
            DataFrame with columns: date, amount, description, source
        """
        try:
            df_raw = pd.read_csv(
                file_path_or_buffer, 
                sep=';', 
                encoding='latin1', 
                skiprows=2, 
                index_col=False
            )
        except Exception:
            # Fallback if skiprows varies
            df_raw = pd.read_csv(
                file_path_or_buffer, 
                sep=';', 
                encoding='latin1', 
                header=2
            )
            
        # Generic cleanup
        df_raw.columns = [c.strip() for c in df_raw.columns]
        
        # Verify required columns exist
        required = ['Data', 'Valor', 'Débito', 'Crédito', 'Complemento']
        if not all(col in df_raw.columns for col in required):
            logger.warning(f"CSV Missing columns. Found: {list(df_raw.columns)}")
            return pd.DataFrame()
            
        transactions = []
        
        for _, row in df_raw.iterrows():
            try:
                date_str = row['Data']
                if pd.isna(date_str): 
                    continue
                
                dt = datetime.strptime(date_str, "%d/%m/%Y").date()
                
                complement = str(row['Complemento']).strip()
                
                # Parse Amount (handles multiple formats)
                val_raw = str(row['Valor']).strip()
                amount = self._parse_amount_flexible(val_raw)
                    
                transactions.append({
                    'date': dt,
                    'amount': amount,
                    'description': complement,
                    'source': 'Ledger'
                })
                
            except Exception as e:
                logger.debug(f"Skipping row: {e}")
                continue
                
        return pd.DataFrame(transactions)
    
    def _parse_amount_flexible(self, val_raw: str) -> float:
        """
        Parse amount from various formats.
        
        Handles:
        - Brazilian: 1.000,00 -> 1000.00
        - European: 1000,00 -> 1000.00
        - US: 1,000.00 -> 1000.00
        """
        if ',' in val_raw and '.' in val_raw:
            # 1.000,00 -> 1000.00 (Brazilian)
            val_clean = val_raw.replace('.', '').replace(',', '.')
        elif ',' in val_raw:
            # 1000,00 -> 1000.00 (European)
            val_clean = val_raw.replace(',', '.')
        else:
            # Already float string
            val_clean = val_raw
            
        return abs(float(val_clean))
