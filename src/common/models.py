from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class UnifiedTransaction:
    """
    Canonical representation of a bank transaction.
    Used to standardize data between Extractor, Reconciler, and OFX Generator.
    """
    date: datetime
    amount: float
    memo: str
    type: str # 'DEBIT', 'CREDIT', 'OTHER'
    doc_id: Optional[str] = None # Document number / Check number
    fitid: Optional[str] = None # Financial Institution Transaction ID (Unique)
    internal_id: Optional[int] = None # Internal sequence ID for deduplication
    source_file: Optional[str] = None # Source filename
    
    def to_dict(self):
        return {
            'date': self.date,
            'amount': self.amount,
            'memo': self.memo,
            'type': self.type,
            'doc_id': self.doc_id,
            'fitid': self.fitid,
            'internal_id': self.internal_id,
            'source_file': self.source_file
        }
