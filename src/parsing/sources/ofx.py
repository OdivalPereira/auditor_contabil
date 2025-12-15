"""
OFX File Parser

Parses OFX (Open Financial Exchange) files for bank statement data.
"""
import io
import re
import logging
import pandas as pd
from ofxparse import OfxParser as LibOfxParser
from ..base import BaseParser

logger = logging.getLogger(__name__)


class OfxParser(BaseParser):
    """
    Parser for OFX bank statement files.
    
    Handles encoding issues common in Brazilian bank OFX files.
    """
    
    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        transactions = []
        metadata = {
            'bank': '', 
            'agency': '', 
            'account': '', 
            'start_date': None, 
            'end_date': None
        }
        
        try:
            # 1. Read content as string (handling encoding)
            if isinstance(file_path_or_buffer, str):
                with open(file_path_or_buffer, 'rb') as f:
                    raw = f.read()
            else:
                if isinstance(file_path_or_buffer, bytes):
                    raw = file_path_or_buffer
                else:
                    raw = file_path_or_buffer.read()
                    if isinstance(raw, str):
                        raw = raw.encode('cp1252', errors='ignore')
            
            # Decode using cp1252 (ignore undefined bytes)
            content = raw.decode('cp1252', errors='ignore')
            
            # 2. Replace encoding declaration to avoid confusion
            content = re.sub(
                r'encoding=["\'].*?["\']', 
                'encoding="UTF-8"', 
                content, 
                count=1, 
                flags=re.IGNORECASE
            )
            
            # 3. Parse as UTF-8 BytesIO
            ofx = LibOfxParser.parse(io.BytesIO(content.encode('utf-8')))

            if ofx.account:
                metadata['bank'] = (
                    ofx.account.institution.organization 
                    if ofx.account.institution else ''
                )
                metadata['agency'] = ofx.account.routing_number
                metadata['account'] = ofx.account.number

            for t in ofx.account.statement.transactions:
                transactions.append({
                    'date': t.date.date(),
                    'amount': t.amount,
                    'description': t.memo,
                    'source': 'Bank'
                })
                
        except Exception as e:
            logger.error(f"Error parsing OFX: {e}")
            return pd.DataFrame(columns=['date', 'amount', 'description', 'source']), metadata
            
        df = pd.DataFrame(transactions)
        
        if not df.empty:
            metadata['start_date'] = df['date'].min()
            metadata['end_date'] = df['date'].max()
            
        return df, metadata
