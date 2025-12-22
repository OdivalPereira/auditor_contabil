import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

import re
from datetime import datetime

class SicrediPDFParser(BaseParser):
    bank_name = 'Sicredi'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        return self.parse_pdf(file_path_or_buffer)

    def extract_page(self, page):
        text = page.extract_text() or ""
        
        if "Associado:" in text and "Cooperativa:" in text:
            return self._extract_associado(page)
        elif "COOP CRED" in text:
            return self._extract_standard(page)
            
        return self.extract_transactions_smart(page)

    def _extract_standard(self, page):
        """
        Specialized extraction for Sicredi Standard (COOP CRED) layout.
        Coordinates: Debit (~370), Credit (~452), Balance (~529)
        """
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        # 05/12/2005 S A L D O A N T E R I O R 14.493,76
        start_bal_match = re.search(r"S A L D O\s+A N T E R I O R\s+([\d\.,]+)", text)
        if start_bal_match:
            bal_start = self._parse_br_amount(start_bal_match.group(1))

        words = page.extract_words()
        lines = {}
        for w in words:
            top = int(w['top'] // 2) * 2
            if top not in lines: lines[top] = []
            lines[top].append(w)
            
        for top in sorted(lines.keys()):
            line_words = sorted(lines[top], key=lambda x: x['x0'])
            
            # Find date
            dt_words = [w['text'] for w in line_words if w['x0'] < 100]
            dt_s = "".join(dt_words)
            if not re.match(r"\d{2}/\d{2}/\d{4}", dt_s): continue
            
            # Identify columns
            # Debit: ~330-410, Credit: ~410-490, Balance: ~490-600
            deb_words = [w['text'] for w in line_words if 330 < w['x0'] < 410]
            cre_words = [w['text'] for w in line_words if 410 <= w['x0'] < 490]
            bal_words = [w['text'] for w in line_words if w['x0'] >= 490]
            desc_words = [w['text'] for w in line_words if 150 <= w['x0'] < 330]
            
            memo = " ".join(desc_words).strip()
            val_deb = "".join(deb_words)
            val_cre = "".join(cre_words)
            bal_s = "".join(bal_words)
            
            amount = 0.0
            if val_cre:
                amount = self._parse_br_amount(val_cre)
            elif val_deb:
                amount = -abs(self._parse_br_amount(val_deb))

            if amount != 0:
                try:
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    br = self._parse_br_amount(bal_s) if bal_s else None
                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': memo,
                        'bal_row': br,
                        'source': 'Bank'
                    })
                    if br is not None: bal_end = br
                except: continue
                
        return rows, bal_start, bal_end

    def _extract_associado(self, page):
        """
        Layout with columns: Data | Descrição | Documento | Valor (R$) | Saldo (R$)
        """
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        # SALDO ANTERIOR 33.971,01
        start_bal_match = re.search(r"SALDO ANTERIOR\s+([\d\.,]+)", text)
        if start_bal_match:
            bal_start = self._parse_br_amount(start_bal_match.group(1))

        # 02/01/2025 APLIC.FINANC.AVISO PREVIO CAPTACAO -100,00 33.871,01
        txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(.*?)\s+(-?[\d\.,]+)\s+([\d\.,]+)")

        for line in lines:
            m = txn_pattern.search(line)
            if m:
                dt_s, desc, val_s, bal_s = m.groups()
                try:
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    amount = self._parse_br_amount(val_s)
                    if "-" in val_s: amount = -abs(amount)
                    
                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc.strip(),
                        'source': 'Bank'
                    })
                    bal_end = self._parse_br_amount(bal_s)
                except: continue

        if not rows:
            return self.extract_transactions_smart(page)
        return rows, bal_start, bal_end

    def _extract_standard(self, page):
        """
        Layout for SICREDI 09 2025.pdf
        """
        # Usually similar but with different headers
        return self.extract_transactions_smart(page)
