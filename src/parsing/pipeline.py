"""
Extractor Pipeline

Orchestrates the PDF extraction process with automatic layout detection,
text-based extraction, OCR fallback, and auto-correction heuristics.
"""
from src.common.logging_config import get_logger
import pdfplumber
from typing import Dict, Any
from .config.registry import LayoutRegistry
from .extractors.generic import GenericPDFExtractor
from .extractors.ocr import OCRExtractor
from src.common.models import UnifiedTransaction
import os
import dataclasses
from .extractors.ai_generation import GeminiLayoutGenerator

logger = get_logger(__name__)


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
            logger.error(f"PDF Read Error: {e}", file_path=file_path, error_type=type(e).__name__)
            result['error'] = f"PDF Read Error: {e}"
            return result

        # 2. Detect Layout
        layout = self.registry.detect(full_text_sample)
        
        # AI Fallback
        if not layout and len(full_text_sample.strip()) > 50:
             try:
                 logger.info("Layout not detected. Attempting AI Layout Generation...", text_length=len(full_text_sample))
                 ai_gen = GeminiLayoutGenerator(api_key=os.getenv('GEMINI_API_KEY'))
                 generated_layout = ai_gen.generate_layout(full_text_sample)
                 
                 if generated_layout:
                     logger.info(f"AI generated layout: {generated_layout.name}", bank_id=generated_layout.bank_id)
                     # Save to registry
                     self.registry.save_layout(dataclasses.asdict(generated_layout))
                     layout = generated_layout
             except Exception as e:
                 logger.error(f"AI Generation failed: {e}", exc_info=True)

        if not layout:
            if len(full_text_sample.strip()) < 50:
                logger.warning("Low text confidence. Assuming scanned PDF, but layout not detected.", text_length=len(full_text_sample))
            result['error'] = "Layout not detected in Text mode."
            return result
        
        result['layout'] = layout.name
        logger.info(f"Layout detected: {layout.name}", layout_owner=layout.bank_id)

        # 3. Choose Specialized Parser or Generic Extractor
        from .banks import PARSERS
        
        parser_cls = PARSERS.get(layout.bank_id)
        if not parser_cls:
            # Try lookup by normalized name if bank_id fails
            name_key = layout.name.upper().replace(" ", "")
            parser_cls = PARSERS.get(name_key)
            
        if parser_cls:
            logger.info(f"Using specialized parser: {parser_cls.__name__}", parser_type="specialized")
            parser = parser_cls()
        else:
            logger.info(f"Using GenericPDFExtractor for layout: {layout.name}", parser_type="generic")
            parser = GenericPDFExtractor(layout)

        extractor = parser
        
        # Auto-correction loop
        max_attempts = 3
        best_result = None
        
        for attempt in range(max_attempts):
            logger.debug(f"Extraction attempt {attempt+1}/{max_attempts}", attempt=attempt+1)
            
            data = extractor.extract(file_path)
            transactions_dict = data['transactions']
            validation = data.get('validation', {})
            
            if best_result is None:
                best_result = data
            
            # Check if valid
            if validation.get('is_valid'):
                logger.info("Extraction validated successfully.", tx_count=len(transactions_dict))
                best_result = data
                break
                
            # Try heuristics if invalid
            diff = validation.get('diff', 0.0)
            if diff > 0.001:
                logger.warning(f"Divergence detected: {diff:.2f}")
                
                fixed = self._try_sign_flip_heuristic(data, transactions_dict)
                if fixed:
                    logger.info("Heuristic A (Sign Flip) fixed the discrepancy.", method="sign_flip")
                    best_result = data
                    break
                
                fixed = self._try_ghost_recovery_heuristic(data, transactions_dict)
                if fixed:
                    logger.info("Heuristic B (Ghost Recovery) fixed the discrepancy.", method="ghost_recovery")
                    best_result = data
                    break
            
            logger.warning("Heuristics failed to fix automatically.", diff=diff)
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
                    logger.info("Transactions recovered via OCR.", tx_count=len(transactions))
                else:
                    result['method'] = 'Failed'
                    logger.error("OCR failed to find transactions.")

            # Standardize to UnifiedTransaction
            unified_txs = []
            for tx in transactions:
                unified_txs.append(UnifiedTransaction(
                    date=tx['date'],
                    amount=tx['amount'],
                    memo=tx['memo'],
                    type=tx.get('type', 'OTHER'),
                    doc_id=tx.get('doc_id'),
                    fitid=tx.get('fitid'),
                    internal_id=tx.get('internal_id'),
                    source_file=tx.get('source_file', os.path.basename(file_path))
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
