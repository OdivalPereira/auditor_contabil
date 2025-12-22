import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

import re
from datetime import datetime

class BradescoPDFParser(BaseParser):
    bank_name = 'Bradesco'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        self.current_date = None
        return self.parse_pdf(file_path_or_buffer)

    def _parse_br_amount(self, amount_str) -> float:
        """Overridden to keep sign for balances."""
        if not amount_str: return 0.0
        if isinstance(amount_str, (float, int)): return float(amount_str)
        
        # Remove thousand separator and handle decimal
        clean_str = str(amount_str).replace('.', '').replace(',', '.')
        try:
            val = float(clean_str)
            # Preserve minus sign if present in original string
            if "-" in str(amount_str) and val > 0:
                return -val
            return val
        except ValueError:
            return 0.0

    def extract_page(self, page):
        """
        Specialized extraction for Bradesco layouts.
        Uses a stateful approach to handle missing dates and multi-line descriptions.
        """
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        
        # 1. Detect Date Range from Header (don't reset self.current_date here)
        # Extrato de: Ag: 189 | CC: 0027894-7 | Entre 01/01/2025 e 31/01/2025
        header_range = re.search(r"Entre\s+(\d{2}/\d{2}/\d{4})\s+e\s+(\d{2}/\d{2}/\d{4})", text)
        page_start_date = None
        page_end_date = None
        if header_range:
            try:
                page_start_date = datetime.strptime(header_range.group(1), "%d/%m/%Y").date()
                page_end_date = datetime.strptime(header_range.group(2), "%d/%m/%Y").date()
            except: pass

        # 2. Check for starting balance on the page
        start_bal_match = re.search(r"(\d{2}/\d{2}/\d{4})\s+SALDO ANTERIOR\s+([-]?[\d\.,]+)", text)
        if start_bal_match:
            bal_start = self._parse_br_amount(start_bal_match.group(2))
        
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
            
            # Skip noise and summary lines
            upper_text = line_text.upper()
            if not line_text or "EXTRATO DE" in upper_text or "SALDO ANTERIOR" in upper_text or "LANÇAMENTO" in upper_text:
                continue
                
            # If we hit a TOTAL line WITH a balance, this usually marks the end of the CC section
            if "TOTAL" in upper_text and any(w['x0'] > 510 for w in line_words):
                if current_tx and current_tx['date']:
                    rows.append(current_tx)
                current_tx = None
                
                nums_footer = []
                for w in line_words:
                    txt = w['text']
                    if re.match(r"^-?[\d\.,]+$", txt) and len(txt) > 2 and w['x0'] > 510:
                        nums_footer.append(self._parse_br_amount(txt))
                if nums_footer:
                    bal_end = nums_footer[-1]
                break # Stop processing this page after footer/summary
                
            # 1. Detect Date at the start of the line
            dt_words = [w['text'] for w in line_words if w['x0'] < 100]
            dt_s = "".join(dt_words)
            if re.match(r"\d{2}/\d{2}/\d{4}", dt_s):
                try:
                    self.current_date = datetime.strptime(dt_s, "%d/%m/%Y").date()
                except: pass

            # 2. Extract numeric values and their potential roles
            # Bradesco Columns: Credit (330-410), Debit (410-505), Balance (>510)
            nums = [] # (value, x0, original_text)
            for w in line_words:
                txt = w['text']
                if re.match(r"^-?[\d\.,]+$", txt) and len(txt) > 2 and w['x0'] > 320:
                    nums.append((self._parse_br_amount(txt), w['x0'], txt))
            
            # 3. Decision Logic
            is_money_line = any(330 < n[1] < 505 for n in nums)
            is_balance_only = not is_money_line and any(n[1] > 510 for n in nums)
            
            # Description parts (always in the middle)
            desc_parts = [w['text'] for w in line_words if 95 < w['x0'] < 330]
            desc_line = " ".join(desc_parts).strip()
            
            if is_money_line:
                # This physical line contains an amount or a balance (or both)
                # If we have a pending transaction, save it
                if current_tx and current_tx['date']:
                    rows.append(current_tx)
                current_tx = None
                
                amount = 0.0
                br_val = None
                
                if len(nums) >= 2:
                    val, x0, orig = nums[-2] 
                    b_val, b_x0, b_orig = nums[-1]
                    
                    if b_x0 > 510:
                        br_val = b_val
                        bal_end = br_val
                        amount = val
                        if x0 > 410 or "-" in orig: amount = -abs(amount)
                        else: amount = abs(amount)
                    else:
                        amount = b_val
                        if b_x0 > 410 or "-" in b_orig: amount = -abs(amount)
                        else: amount = abs(amount)
                elif len(nums) == 1:
                    val, x0, orig = nums[0]
                    amount = val
                    if x0 > 410 or "-" in orig: amount = -abs(amount)
                    else: amount = abs(amount)
                
                # Apply Date Filter based on header range
                is_in_range = True
                if self.current_date:
                    if page_start_date and self.current_date < page_start_date: is_in_range = False
                    if page_end_date and self.current_date > page_end_date: is_in_range = False
                
                if self.current_date and is_in_range:
                    current_tx = {
                        'date': self.current_date,
                        'amount': amount,
                        'description': desc_line,
                        'bal_row': br_val,
                        'source': 'Bank'
                    }
            elif is_balance_only:
                # Update row balance and end balance but don't count as transaction
                if current_tx and current_tx['date']:
                    rows.append(current_tx)
                current_tx = None
                
                # Update bal_end if we are in range
                if not page_end_date or (self.current_date and self.current_date <= page_end_date):
                    bal_res = [n for n in nums if n[1] > 510]
                    if bal_res:
                        bal_end = bal_res[-1][0]
            else:
                # Just description text
                if current_tx and desc_line:
                    current_tx['description'] = (current_tx['description'] + " " + desc_line).strip()

        # Flush last tx
        if current_tx and current_tx['date']:
            rows.append(current_tx)
            
        txns = [r for r in rows if r['date'] is not None and abs(r['amount']) > 0.001]

        if not txns and not bal_start and not bal_end:
            # Check if page is just headers or noise
             pass
             
        return txns, bal_start, bal_end
