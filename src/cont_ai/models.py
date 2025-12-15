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
    
    def to_dict(self):
        return {
            'date': self.date,
            'amount': self.amount,
            'memo': self.memo,
            'type': self.type,
            'doc_id': self.doc_id,
            'fitid': self.fitid
        }
