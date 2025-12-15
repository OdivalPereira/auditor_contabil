"""
AI-powered Layout Generator

Uses Google Gemini API to automatically generate bank layout configurations
from PDF text samples.
"""
import json
import re
import logging
from typing import Optional

from ..config.layout import BankLayout, ColumnDef

logger = logging.getLogger(__name__)


class GeminiLayoutGenerator:
    """
    AI-powered layout generator using Google Gemini.
    
    Analyzes PDF text samples and generates JSON layout configurations
    with regex patterns for transaction extraction.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize generator with API key.
        
        Args:
            api_key: Google Gemini API key
        """
        if not api_key:
            # Try to get from env if not provided directly
            import os
            api_key = os.getenv('GEMINI_API_KEY')
            
        if not api_key:
            raise ValueError("API Key is required for Gemini Layout Generator")
            
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def generate_layout(self, text_sample: str) -> Optional[BankLayout]:
        """
        Analyze text sample and generate layout configuration.
        
        Args:
            text_sample: Extracted text from PDF
            
        Returns:
            BankLayout object or None if generation fails
        """
        prompt = f"""
        You are an expert in parsing Bank Statements.
        Analyze the following text extracted from a PDF.
        Your goal is to create a configuration to automatically parse this statement in the future.
        
        1. **Identify the Bank**: Extract the bank name.
        2. **Keywords**: Identify 2-3 unique strings that appear in this document and verify it's from this specific bank (e.g. "Banco do Brasil", "Extrato Mensal", "CNPJ: ...").
        3. **Transaction Pattern**: Create a Python Regular Expression (regex) to capture ONE transaction line.
           - Ignore headers, balances, summary lines.
           - The regex MUST have capturing groups for: date, amount, memo.
           - If lines are split, assume they are joined by spaces.
        
        4. **Schema Map**: Map the regex groups to standard columns:
           - "date": Date of transaction
           - "memo": Description
           - "amount": Value (signed or unsigned)
           - "type": (Optional) 'D' or 'C' indicator.
           
        Text Sample:
        ---
        {text_sample[:4000]}
        ---

        Return strictly valid JSON (no markdown) matching this structure:
        {{
            "name": "Bank Name - Type",
            "bank_id": "Number or Code",
            "keywords": ["keyword1", "keyword2"],
            "line_pattern": "^(\d{{2}}/\d{{2}})....",
            "columns": [
                {{ "name": "date", "match_group": 1 }},
                {{ "name": "memo", "match_group": 2 }},
                {{ "name": "amount", "match_group": 3 }}
            ],
            "amount_decimal_separator": ",", 
            "amount_thousand_separator": ".",
            "date_format": "%d/%m/%Y"
        }}
        
        IMPORTANT: 
        - Regex must be valid Python `re` syntax. 
        - Escape backslashes (e.g. \\d).
        - 'match_group' indices are 1-based.
        """
        
        try:
            response = self.model.generate_content(prompt)
            raw_text = response.text
            
            # Sanitize response
            clean_text = raw_text.replace("```json", "").replace("```", "").strip()
            
            layout_config = json.loads(clean_text)
            logger.info(f"Generated layout for bank: {layout_config.get('name', 'Unknown')}")
            
            # Convert to BankLayout
            columns_data = layout_config.pop('columns', [])
            columns = [ColumnDef(**c) for c in columns_data]
            
            # Ensure name exists
            if 'name' not in layout_config:
                layout_config['name'] = f"New AI Layout {layout_config.get('bank_id', 'Unknown')}"
            
            return BankLayout(columns=columns, **layout_config)
            
        except Exception as e:
            logger.error(f"Gemini Generation Error: {e}")
            return None
