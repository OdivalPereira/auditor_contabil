import pandas as pd
import pdfplumber
import logging
import re
from datetime import datetime
from ..base import BaseParser

logger = logging.getLogger(__name__)

class ItauPDFParser(BaseParser):
    bank_name = 'Itau'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        return self.parse_pdf(file_path_or_buffer)

    def extract_page(self, page):
        text = page.extract_text() or ""
        
        # Sub-layout: Sagrado / Modern
        if "Saldo total" in text and "Lançamentos do período" in text:
            return self._extract_sagrado(page)
            
        # Default to smart extraction for other Itau layouts
        return self.extract_transactions_smart(page)

    def _extract_sagrado(self, page):
        """
        Specialized extraction for the 'Sagrado' Itau layout.
        Features columns: Data | Lançamentos | Razão Social | CNPJ/CPF | Valor (R$) | Saldo (R$)
        """
        rows = []
        bal_start = None
        bal_end = None
        
        # Extract starting balance from the header area if possible
        first_page_text = page.extract_text() or ""
        start_bal_match = re.search(r"(\d{2}/\d{2}/\d{4})\s+SALDO ANTERIOR\s+([\d\.,]+)", first_page_text)
        if start_bal_match:
            bal_start = self._parse_br_amount(start_bal_match.group(2))

        # Use coordinate-based extraction to separate columns
        words = page.extract_words()
        lines = {}
        for w in words:
            # Group words by Y coordinate with some tolerance
            top = int(w['top'] // 2) * 2
            if top not in lines: lines[top] = []
            lines[top].append(w)
            
        seen_lines = set()

        for top in sorted(lines.keys()):
            line_words = sorted(lines[top], key=lambda x: x['x0'])
            line_text = " ".join([w['text'] for w in line_words])
            
            # Anti-duplication by content + y
            content_key = f"{top}_{line_text}"
            if content_key in seen_lines: continue
            seen_lines.add(content_key)

            # Identify columns by x0
            # Data (~35), Lançamentos (~100-250), Razão Social (~280), CNPJ (~360), Valor (~480), Saldo (~520)
            dt_words = [w['text'] for w in line_words if w['x0'] < 100]
            val_words = [w['text'] for w in line_words if 450 < w['x0'] < 518]
            bal_words = [w['text'] for w in line_words if w['x0'] >= 518]
            desc_words = [w['text'] for w in line_words if 100 <= w['x0'] <= 450]
            
            dt_s = "".join(dt_words)
            if not re.search(r"\d{2}/\d{2}/\d{4}", dt_s): continue
            
            memo = " ".join(desc_words).strip()
            if "SALDO ANTERIOR" in memo.upper(): continue
            
            val_s = "".join(val_words)
            bal_s = "".join(bal_words)
            
            if val_s:
                amount = self._parse_br_amount(val_s)
                # Sign detection by keywords in memo
                memo_up = memo.upper()
                
                # Positive markers
                pos_keys = ['PIX QR', 'CREDITO', 'RECEBIDO', 'ESTORNO', 'RESGATE', 'DEP.', 'RENDIMENTO']
                # Negative markers
                neg_keys = [
                    'PIX ENVIADO', 'DEBITO', 'PAGTO', 'TARIFA', 'MANUT', 'DOC/TED', 
                    'CP MAESTRO', 'EST SHOP', 'SISPAG', 'PAG.', 'CH COMPENSADO', 
                    'DÉBITO', 'TRANSFERENCIA E', 'PGTO', 'IOF', 'JUROS'
                ]

                if "-" in val_s: 
                    amount = -abs(amount)
                elif any(k in memo_up for k in pos_keys):
                    amount = abs(amount)
                elif any(k in memo_up for k in neg_keys):
                    amount = -abs(amount)
                else:
                    # Default for unknown: If it's Itau Sagrado, usually payments have '-' in val_s
                    # but some might not. Let's assume negative if not matched as positive?
                    # No, safer to stay positive and let reconciliation fail/check.
                    pass

                try:
                    dt = datetime.strptime(dt_s[:10], "%d/%m/%Y").date()
                    br = self._parse_br_amount(bal_s) if bal_s else None
                    rows.append({
                        'date': dt, 
                        'amount': amount, 
                        'description': memo, 
                        'bal_row': br,
                        'source': 'Bank'
                    })
                    if bal_s:
                        bal_end = br
                except: continue

        if not rows:
            return self.extract_transactions_smart(page)
            
        return rows, bal_start, bal_end
