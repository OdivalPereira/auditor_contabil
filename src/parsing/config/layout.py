"""
Bank Layout Configuration

Defines dataclasses for configuring bank-specific PDF parsing rules.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ColumnDef:
    """
    Defines how to extract a specific field from a line/area.
    
    Attributes:
        name: Field name ('date', 'amount', 'doc_id', 'memo', 'type')
        match_group: Regex group number (1-indexed)
    """
    name: str
    match_group: Optional[int] = None


@dataclass
class BankLayout:
    """
    Configuration for a Bank PDF Layout.
    
    Used by GenericPDFExtractor to parse transactions from PDFs
    using regex patterns defined per bank.
    
    Attributes:
        name: Human-readable layout name (e.g. "Banco do Brasil - Mensal")
        bank_id: Bank code (e.g. "001" for BB)
        keywords: List of strings to identify this layout in PDF text
        line_pattern: Regex pattern to match transaction lines
        columns: List of ColumnDef mapping regex groups to fields
    """
    name: str
    bank_id: str
    keywords: List[str]
    line_pattern: str 
    columns: List[ColumnDef]
    
    # Optional logic flags
    has_balance_cleanup: bool = True
    amount_decimal_separator: str = ','
    amount_thousand_separator: str = '.'
    date_format: str = '%d/%m/%Y'
    
    # Metadata extraction (Header)
    header_keywords: List[str] = field(default_factory=list)
    
    # Balance Verification Patterns
    balance_start_pattern: Optional[str] = None 
    balance_end_pattern: Optional[str] = None
