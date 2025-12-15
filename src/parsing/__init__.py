"""
Unified Parsing Module for Cont.AI

This module consolidates all parsing functionality:
- Bank PDF parsers (BB, Stone, Sicredi)
- Source parsers (OFX, Ledger PDF/CSV)
- Generic extractors (Text, OCR, AI)
- Pipeline orchestration
"""

# Base classes
from .base import BaseParser, BaseExtractor

# Configuration
from .config.layout import BankLayout, ColumnDef
from .config.registry import LayoutRegistry

# Banks
from .banks.bb import BBPdfParser, BBMonthlyPDFParser
from .banks.stone import StonePDFParser

# Sources
from .sources.ofx import OfxParser
from .sources.ledger_pdf import LedgerParser
from .sources.ledger_csv import LedgerCSVParser

# Extractors
from .extractors.generic import GenericPDFExtractor
from .extractors.ocr import OCRExtractor
from .extractors.ai_generation import GeminiLayoutGenerator

# Pipeline & Factory
from .pipeline import ExtractorPipeline
from .facade import ParserFacade

__all__ = [
    # Base
    'BaseParser',
    'BaseExtractor',
    # Config
    'BankLayout',
    'ColumnDef', 
    'LayoutRegistry',
    # Banks
    'BBPdfParser',
    'BBMonthlyPDFParser',
    'StonePDFParser',
    # Sources
    'OfxParser',
    'LedgerParser',
    'LedgerCSVParser',
    # Extractors
    'GenericPDFExtractor',
    'OCRExtractor',
    'GeminiLayoutGenerator',
    # Pipeline
    'ExtractorPipeline',
    'ParserFacade',
]
