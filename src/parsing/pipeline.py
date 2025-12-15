"""
Extractor Pipeline

Orchestrates the PDF extraction process with automatic layout detection,
text-based extraction, OCR fallback, and auto-correction heuristics.
"""
import logging
import pdfplumber
from typing import Dict, Any
from .config.registry import LayoutRegistry
from .extractors.generic import GenericPDFExtractor
from .extractors.ocr import OCRExtractor
from src.common.models import UnifiedTransaction
import os
import dataclasses
from .extractors.ai_generation import GeminiLayoutGenerator

logger = logging.getLogger(__name__)


class ExtractorPipeline:
    """
    Main orchestrator for PDF extraction.
    
    Handles:
    - Layout detection from PDF text
    - Text-based extraction with GenericPDFExtractor
    - Auto-correction heuristics for balance discrepancies
    - OCR fallback for scanned PDFs
    """
    
    def __init__(self, registry: LayoutRegistry):
        """
        Initialize pipeline with layout registry.
        
        Args:
            registry: LayoutRegistry with available bank layouts
        """
        self.registry = registry

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a PDF file and extract transactions.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dict with transactions, account_info, method, layout, error
        """
        result = {
            'transactions': [],
            'account_info': {},
            'method': 'unknown',
            'layout': 'unknown',
            'error': None
        }

        # 1. Peek at text for Layout Detection
        try:
            full_text_sample = ""
            with pdfplumber.open(file_path) as pdf:
                if len(pdf.pages) > 0:
                    full_text_sample = pdf.pages[0].extract_text() or ""
        except Exception as e:
            result['error'] = f"PDF Read Error: {e}"
            return result

        # 2. Detect Layout
        layout = self.registry.detect(full_text_sample)
        
        # AI Fallback
        if not layout and len(full_text_sample.strip()) > 50:
             try:
                 logger.info("Layout not detected. Attempting AI Layout Generation...")
                 ai_gen = GeminiLayoutGenerator(api_key=os.getenv('GEMINI_API_KEY'))
                 generated_layout = ai_gen.generate_layout(full_text_sample)
                 
                 if generated_layout:
                     logger.info(f"AI generated layout: {generated_layout.name}")
                     # Save to registry
                     self.registry.save_layout(dataclasses.asdict(generated_layout))
                     layout = generated_layout
             except Exception as e:
                 logger.error(f"AI Generation failed: {e}")

        if not layout:
            if len(full_text_sample.strip()) < 50:
                logger.warning("Low text confidence. Assuming scanned PDF, but layout not detected.")
            result['error'] = "Layout not detected in Text mode."
            return result
        
        result['layout'] = layout.name

        # 3. Try Generic Extractor with Auto-Correction
        logger.info(f"Trying Extractor with layout: {layout.name}")
        
        # 3. Try Generic Extractor with Auto-Correction
        logger.info(f"Trying Extractor with layout: {layout.name}")
        
        # Mapping Layout Name -> Specialized Parser Class
        # Imports done inside method or top-level? Top level preferred or lazy.
        from .banks.bb import BBPdfParser, BBMonthlyPDFParser
        from .banks.cef import CEFPdfParser
        from .banks.sicredi import SicrediPDFParser
        from .banks.santander import SantanderPDFParser
        from .banks.stone import StonePDFParser
        from .banks.itau import ItauPDFParser
        from .banks.cresol import CresolParser
        
        extractor = None
        name_lower = layout.name.lower()
        
        if "banco do brasil" in name_lower or "bb" in name_lower:
            # Check if receipt or monthly?
            # For now assume Monthly PDF logic holds
            extractor = BBMonthlyPDFParser() 
        elif "caixa" in name_lower or "cef" in name_lower:
            extractor = CEFPdfParser()
        elif "sicredi" in name_lower:
            extractor = SicrediPDFParser()
        elif "santander" in name_lower:
            extractor = SantanderPDFParser()
        elif "stone" in name_lower:
            extractor = StonePDFParser()
        elif "itau" in name_lower or "itaú" in name_lower:
            extractor = ItauPDFParser()
        elif "cresol" in name_lower:
             extractor = CresolParser(layout)
        else:
            extractor = GenericPDFExtractor(layout)
        
        # Auto-correction loop
        max_attempts = 3
        best_result = None
        
        for attempt in range(max_attempts):
            logger.debug(f"Extraction attempt {attempt+1}/{max_attempts}")
            
            data = extractor.extract(file_path)
            transactions_dict = data['transactions']
            validation = data.get('validation', {})
            
            if best_result is None:
                best_result = data
            
            # Check if valid
            if validation.get('is_valid'):
                logger.info("Extraction validated successfully.")
                best_result = data
                break
                
            # Try heuristics if invalid
            diff = validation.get('diff', 0.0)
            if diff > 0.001:
                logger.warning(f"Divergence detected: {diff:.2f}")
                
                fixed = self._try_sign_flip_heuristic(data, transactions_dict)
                if fixed:
                    best_result = data
                    break
                
                fixed = self._try_ghost_recovery_heuristic(data, transactions_dict)
                if fixed:
                    best_result = data
                    break
            
            logger.warning("Heuristics failed to fix automatically.")
            break 
        
        # Use best result
        data = best_result
        transactions = data.get('transactions', [])
        result['account_info'] = data.get('account_info', {})
        result['balance_info'] = data.get('balance_info', {})
        result['validation'] = data.get('validation', {})
        result['method'] = 'Text (Auto-Corrected)' if 'Corrigido' in str(result['validation'].get('msg')) else 'Text'
        
        try:
            # Fallback to OCR if no transactions
            if len(transactions) == 0:
                logger.warning("No transactions found via Text. Attempting OCR...")
                
                ocr_extractor = OCRExtractor(layout, GenericPDFExtractor)
                ocr_data = ocr_extractor.extract(file_path)
                
                if len(ocr_data['transactions']) > 0:
                    transactions = ocr_data['transactions']
                    result['account_info'] = ocr_data['account_info']
                    result['method'] = 'OCR'
                else:
                    result['method'] = 'Failed'

            # Standardize to UnifiedTransaction
            unified_txs = []
            for tx in transactions:
                unified_txs.append(UnifiedTransaction(
                    date=tx['date'],
                    amount=tx['amount'],
                    memo=tx['memo'],
                    type=tx.get('type', 'OTHER'),
                    doc_id=tx.get('doc_id'),
                    fitid=tx.get('fitid')
                ))
            
            result['transactions'] = unified_txs
            
        except Exception as e:
            result['error'] = str(e)

        return result
    
    def _try_sign_flip_heuristic(self, data: Dict, transactions: list) -> bool:
        """Try to fix balance by flipping a transaction's sign."""
        bal_start = data['balance_info'].get('start')
        bal_end = data['balance_info'].get('end')
        
        if bal_start is None or bal_end is None:
            return False
            
        for tx in transactions:
            val = tx['amount']
            potential_change = -2 * val
            
            curr_total = sum(t['amount'] for t in transactions)
            curr_end = bal_start + curr_total
            gap = bal_end - curr_end
            
            if abs(gap - potential_change) < 0.02:
                logger.info(f"Heuristic A: Flipping sign of {val} fixes the gap of {gap:.2f}")
                tx['amount'] = -val
                tx['type'] = 'DEBIT' if tx['amount'] < 0 else 'CREDIT'
                data['validation'] = {'is_valid': True, 'msg': "Corrigido Automaticamente (Inversão de Sinal) 🤖✅"}
                return True
        
        return False
    
    def _try_ghost_recovery_heuristic(self, data: Dict, transactions: list) -> bool:
        """Try to fix balance by recovering a discarded transaction."""
        discarded = data.get('discarded_candidates', [])
        if not discarded:
            return False
            
        bal_start = data['balance_info'].get('start')
        bal_end = data['balance_info'].get('end')
        
        if bal_start is None or bal_end is None:
            return False
            
        curr_total = sum(t['amount'] for t in transactions)
        curr_end = bal_start + curr_total
        gap = bal_end - curr_end
        
        for ghost in discarded:
            ghost_amt = ghost['amount']
            if abs(gap - ghost_amt) < 0.02:
                logger.info(f"Heuristic B: Restoring ghost line {ghost_amt} fixes gap")
                transactions.append(ghost)
                data['validation'] = {'is_valid': True, 'msg': "Corrigido Automaticamente (Linha Restaurada) 🤖✅"}
                return True
        
        return False
