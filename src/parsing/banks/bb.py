import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

import re
from datetime import datetime

class BBMonthlyPDFParser(BaseParser):
    bank_name = 'Banco do Brasil'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        df, metadata = self.parse_pdf(file_path_or_buffer)
        
        # Apply automatic investment reconciliation for BB whenever we have balance info
        if not df.empty and metadata.get('balance_start') is not None and metadata.get('balance_end') is not None:
            df = self._inject_rende_facil_movements(df, metadata['balance_start'], metadata['balance_end'])
        
        return df, metadata
    
    def _inject_rende_facil_movements(self, df: pd.DataFrame, bal_start: float, bal_end: float) -> pd.DataFrame:
        """
        Inject synthetic Rende Fácil transactions to reconcile daily balance gaps.
        BB automatically invests/redeems from Rende Fácil but doesn't show these as transactions.
        """
        df = df.copy()
        df = df.sort_values('date').reset_index(drop=True)
        
        # Group by date and calculate daily net
        daily_summary = df.groupby('date').agg({'amount': 'sum'}).reset_index()
        daily_summary.columns = ['date', 'daily_net']
        
        # Track running balance starting from bal_start
        running_balance = bal_start
        synthetic_rows = []
        
        for _, day in daily_summary.iterrows():
            date = day['date']
            daily_net = day['daily_net']
            
            # Calculate what balance would be after this day's transactions
            new_balance = running_balance + daily_net
            
            # Check if we need to inject a Rende Fácil movement
            # This happens when the calculated balance differs from what we expect
            # (implying an automatic investment/redemption occurred)
            
            # For the last day, we know the final balance should match bal_end
            is_last_day = (date == daily_summary.iloc[-1]['date'])
            
            if is_last_day:
                # On the last day, inject whatever is needed to reach bal_end
                if abs(new_balance - bal_end) > 0.01:
                    adjustment = bal_end - new_balance
                    synthetic_rows.append({
                        'date': date,
                        'amount': adjustment,
                        'description': 'Rende Fácil - Movimentação Automática',
                        'bal_row': None,
                        'source': 'System'
                    })
                    running_balance = bal_end
                else:
                    running_balance = new_balance
            else:
                # For other days, assume balance should return to bal_start after auto-movements
                target_balance = bal_start
                if abs(new_balance - target_balance) > 0.01:
                    adjustment = target_balance - new_balance
                    synthetic_rows.append({
                        'date': date,
                        'amount': adjustment,
                        'description': 'Rende Fácil - Movimentação Automática',
                        'bal_row': None,
                        'source': 'System'
                    })
                    running_balance = target_balance
                else:
                    running_balance = new_balance
        
        # Add synthetic rows to dataframe
        if synthetic_rows:
            synthetic_df = pd.DataFrame(synthetic_rows)
            df = pd.concat([df, synthetic_df], ignore_index=True)
            df = df.sort_values('date').reset_index(drop=True)
        
        return df

    def extract_page(self, page):
        text = page.extract_text() or ""
        
        if "G331" in text:
            return self._extract_g331(page)
            
        return self.extract_transactions_smart(page)

    def _extract_g331(self, page):
        """
        Specialized extraction for BB G331 monthly layout.
        """
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        # Check for starting balance
        start_bal_match = re.search(r"Saldo Anterior\s+([\d\.,]+)\s+([CD])", text)
        if start_bal_match:
            val = self._parse_br_amount(start_bal_match.group(1))
            if start_bal_match.group(2) == 'D': val = -abs(val)
            bal_start = val

        # Removed ^ anchor to allow prefixes like timestamps/names
        # Using search() instead of match()
        txn_pattern = re.compile(r"(\d{2}/\d{2}/\d{4})\s+(?:\d{2}/\d{2}/\d{4}\s+)?(\d+)\s+(\d+)\s+(.*?)\s+([\d\.,]+)\s+([CD])(?:\s+([\d\.,]+)\s+([CD]))?")

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Specific case for Final Balance line
            if "S A L D O" in line or "Saldo Atual" in line:
                m_bal = re.search(r"([\d\.,]+)\s+([CD])", line)
                if m_bal:
                    val = self._parse_br_amount(m_bal.group(1))
                    if m_bal.group(2) == 'D': val = -abs(val)
                    bal_end = val
                i += 1
                continue
                
            # Skip Start Balance line if matched as a transaction
            if "Saldo Anterior" in line:
                i += 1
                continue

            # Use search to find pattern anywhere in line
            m = txn_pattern.search(line)
            if m:
                dt_s, ag, lote, middle, val_s, sign, bal_s, bal_sign = m.groups()
                
                # Capture prefix if any
                prefix = line[:m.start()].strip()
                
                # Check for continuation on next line
                full_desc = middle.strip()
                if prefix:
                    full_desc = prefix + " " + full_desc
                    
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()
                    if not next_line: j += 1; continue
                    if re.search(r"\d{2}/\d{2}/\d{4}", next_line): break
                    if any(k in next_line.upper() for k in ["SALDO", "S A L D O", "DOCUMENTO", "VALOR", "AGÊNCIA"]): break
                    full_desc += " " + next_line
                    j += 1
                
                try:
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    amount = self._parse_br_amount(val_s)
                    if sign == 'D': amount = -abs(amount)
                    else: amount = abs(amount)
                    
                    br = None
                    if bal_s:
                        br = self._parse_br_amount(bal_s)
                        if bal_sign == 'D': br = -abs(br)
                        bal_end = br

                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': full_desc,
                        'bal_row': br,
                        'source': 'Bank'
                    })
                    i = j - 1 
                except: pass
            else:
                # Debug: Check if we missed a transaction line
                if re.match(r"^\d{2}/\d{2}/\d{4}", line) and "Saldo" not in line and "Lançamentos" not in line:
                    logger.warning(f"BB G331 Skipped possible txn: {line}")
            i += 1

        if not rows:
            return self.extract_transactions_smart(page)
            
        return rows, bal_start, bal_end
