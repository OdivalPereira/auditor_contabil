import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

class SicrediPDFParser(BaseParser):
    bank_name = 'Sicredi'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        return self.parse_pdf(file_path_or_buffer)
