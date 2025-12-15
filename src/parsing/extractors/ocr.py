"""
OCR-based PDF Extractor

Extracts transactions from scanned PDFs using OCR (Tesseract).
"""
import os
import logging
import pytesseract
from pdf2image import convert_from_path
from typing import Dict, Any
from ..base import BaseExtractor
from ..config.layout import BankLayout

logger = logging.getLogger(__name__)

# If Tesseract is not in PATH, specify it here:
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


class OCRExtractor(BaseExtractor):
    """
    OCR-based PDF extractor for scanned documents.
    
    Converts PDF pages to images, runs OCR, then uses
    GenericPDFExtractor to parse the resulting text.
    """
    
    def __init__(self, layout: BankLayout, generic_extractor_cls):
        """
        Initialize OCR extractor.
        
        Args:
            layout: BankLayout configuration
            generic_extractor_cls: GenericPDFExtractor class for text parsing
        """
        self.layout = layout
        self.GenericExtractor = generic_extractor_cls

    def identify(self, pdf_text: str) -> bool:
        """OCR extractor is a fallback, doesn't identify via text."""
        return False 

    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract transactions from scanned PDF.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dict with transactions, account_info, etc.
        """
        logger.info(f"Starting OCR for {os.path.basename(file_path)}")
        
        full_text = ""
        
        try:
            # Convert PDF to images
            images = convert_from_path(file_path)
            
            for i, image in enumerate(images):
                # OCR each page
                text = pytesseract.image_to_string(image, lang='por')
                full_text += f"\n--- Page {i+1} ---\n" + text
                
        except Exception as e:
            logger.error(f"OCR Error: {e}")
            return {'transactions': [], 'account_info': {}, 'error': str(e)}

        # Use GenericExtractor to parse OCR text
        parser = self.GenericExtractor(self.layout)
        return parser.extract_from_text(full_text)
