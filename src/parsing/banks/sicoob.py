import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

import re
from datetime import datetime

class SicoobPDFParser(BaseParser):
    bank_name = 'Sicoob'

    def __init__(self):
        super().__init__()
        self.current_date = None

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        self.current_date = None
        return self.parse_pdf(file_path_or_buffer)

    def _parse_sicoob_amount(self, amount_str) -> float:
        """Parses Sicoob amount with C/D suffix or signals."""
        if not amount_str: return 0.0
        if isinstance(amount_str, (float, int)): return float(amount_str)
        
        txt = str(amount_str).strip().upper()
        sign = 1.0
        if txt.endswith('D') or '-' in txt:
            sign = -1.0
        
        # Clean numeric part
        numeric_part = re.sub(r'[^\d,\.-]', '', txt)
        clean_str = numeric_part.replace('.', '').replace(',', '.')
        try:
            val = float(clean_str)
            return val * sign
        except ValueError:
            return 0.0

    def extract_page(self, page):
        """
        Stateful coordinate-based extraction for Sicoob.
        """
        rows = []
        bal_start = None
        bal_end = None
        
        if not hasattr(self, 'current_date'):
            self.current_date = None
            
        text = page.extract_text() or ""
        
        # 1. Start balance on page
        start_match = re.search(r"SALDO ANTERIOR\s+([\d\.,]+)([CD])", text)
        if start_match:
            bal_start = self._parse_sicoob_amount(start_match.group(1) + start_match.group(2))

        # 2. Page processing
        words = page.extract_words()
        lines_data = {}
        for w in words:
            top = int(w['top'] // 2) * 2
            lines_data.setdefault(top, []).append(w)
            
        current_tx = None
        sorted_tops = sorted(lines_data.keys())
        
        for top in sorted_tops:
            line_words = sorted(lines_data[top], key=lambda x: x['x0'])
            line_text = " ".join([w['text'] for w in line_words]).strip()
            upper_text = line_text.upper()
            
            # 1. Skip strictly structural lines
            if not line_text or any(k in upper_text for k in [
                "SISBR", "COOPERATIVA", "EXTRATO", "LANÇAMENTOS", "DATA DOCUMENTO",
                "CHEQUE ESPECIAL", "LIMITE", "TARIFAS VENCIDAS", "JUROS VENCIDOS", "ENCARGOS",
                "RESUMO", "TAXA", "OUVIDORIA", "SAC:", "CNPJ:"
            ]):
                continue
            
            # 2. Skip ANY line containing SALDO as a summary marker
            # Unless it's somehow part of a description (very rare in Sicoob)
            if "SALDO" in upper_text or "TOTAL" in upper_text:
                # Still try to extract balance from these lines
                # IMPORTANT: Do NOT use "DISPONÍVEL" - it includes cheque especial!
                res = re.search(r"([\d\.,]+)([CD])", line_text)
                if res and (any(k in upper_text for k in ["DIA", "EM CONTA", "ANTERIOR"])):
                    val = self._parse_sicoob_amount(res.group(1) + res.group(2))
                    bal_end = val
                continue

            # 3. Detect Date at x0 < 100 or x0 ~ 171
            dt_words = [w['text'] for w in line_words if w['x0'] < 200]
            dt_s = "".join(dt_words)
            if re.match(r"\d{2}/\d{2}/\d{4}", dt_s):
                try:
                    self.current_date = datetime.strptime(dt_s[:10], "%d/%m/%Y").date()
                except: pass

            # 4. Detect Money Tokens
            nums = []
            for w in line_words:
                txt = w['text']
                if re.search(r"[\d\.,]+[CD\*]$", txt):
                    nums.append((self._parse_sicoob_amount(txt), w['x0'], txt))
            
            # 5. Identify Roles
            # Amount column is widely spaced. SISBR ~438, Standard ~515.
            # We accept anything between 300 and 530 as a candidate for amount.
            is_money_line = any(300 < n[1] < 530 for n in nums)
            
            # Description parts (between date and amount)
            desc_parts = [w['text'] for w in line_words if 95 < w['x0'] < 430]
            desc_line = " ".join(desc_parts).strip()
            # Clean date from description
            desc_line = re.sub(r"^\d{2}/\d{2}/\d{4}\s*", "", desc_line)
            
            if is_money_line:
                # Flush pending
                if current_tx and current_tx['date']:
                    rows.append(current_tx)
                current_tx = None
                
                amount = 0.0
                br_val = None
                
                valid_nums = [n for n in nums if abs(n[0]) > 0.001]
                if len(valid_nums) >= 2:
                    v1, x1, o1 = valid_nums[-2]
                    v2, x2, o2 = valid_nums[-1]
                    if x2 > 525: # Last is balance
                        amount = v1
                        br_val = v2
                    else:
                        amount = v2
                elif len(valid_nums) == 1:
                    val, x0, orig = valid_nums[0]
                    if x0 > 525:
                        br_val = val
                        amount = 0.0
                    else:
                        amount = val
                
                if self.current_date and abs(amount) > 0.001:
                    current_tx = {
                        'date': self.current_date,
                        'amount': amount,
                        'description': desc_line,
                        'bal_row': br_val,
                        'source': 'Bank'
                    }
                elif br_val is not None:
                    bal_end = br_val
            else:
                if current_tx and desc_line:
                    # Append continuation text
                    if not re.match(r"^\d{2}/\d{2}/\d{4}$", desc_line):
                        current_tx['description'] = (current_tx['description'] + " " + desc_line).strip()

        # Flush final
        if current_tx and current_tx['date']:
            rows.append(current_tx)
            
        return [r for r in rows if r['date'] is not None and abs(r['amount']) > 0.001], bal_start, bal_end
