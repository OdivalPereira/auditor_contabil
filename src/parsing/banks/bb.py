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
        
        # Try different BB layouts in order of specificity
        if "G331" in text:
            return self._extract_g331(page)
        
        # Check for the Mod. 0.51 layout (dot dates)
        if self._is_dot_date_layout(text):
            return self._extract_dot_date_layout(page)

        # Check if this is the full format (with agência/lote codes)
        # Sample line: "05/03/2025 3935 99020870 Transferência... 5.186,00 C"
        if self._has_full_format(text):
            return self._extract_full_format(page)
        
        # Otherwise try simplified format
        # Sample line: "02/01/2025 Dep dinheiro ATM"
        # Valor may be on same line or next line
        return self._extract_simplified_format(page)
    
    def _is_dot_date_layout(self, text):
        """Check if the text corresponds to the layout with dot-separated dates."""
        return bool(re.search(r'\d{2}\.\d{2}\.\d{4}', text))

    def _extract_dot_date_layout(self, page):
        """
        Extract transactions from the 'Mod. 0.51' layout (DD.MM.YYYY dates).
        Anchors on lines starting with a date and appends subsequent lines to description.
        Also extracts Start/End balances from "Saldo anterior" or "Saldo" lines.
        """
        rows = []
        bal_start = None
        bal_end = None

        text = page.extract_text() or ""
        lines = text.split('\n')

        # Regex to match a line starting with a date
        # Example: 02.05.2025 870-Transferência recebida 99020 3935 603935000011535 504,00 C
        # Note: We capture everything after date to parse manually because fields vary
        date_line_pattern = re.compile(r'^(\d{2}\.\d{2}\.\d{4})\s+(.*)')

        # Pattern to extract amounts at end of line: VALOR [CD] (optional SALDO [CD])
        # We look for one or two amounts at the end.
        amounts_pattern = re.compile(r'([\d\.,]+)\s+([CD])(?:\s+([\d\.,]+)\s+([CD]))?\s*$')

        current_txn = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if this is a new transaction line (starts with date)
            m_date = date_line_pattern.match(line)
            if m_date:
                # If we had a previous transaction pending (unlikely with this logic as we process immediately,
                # but good for structure if we changed to accumulate lines first), handle it.
                # Actually, in this logic, we will finalize the *previous* transaction before starting a new one?
                # No, we append description lines as we go. But wait, if we process line-by-line,
                # when we hit a date line, the previous transaction is already "done" in terms of capturing its first line,
                # but we need to know if we are currently "inside" a transaction to append description.
                # Since we are iterating, when we hit a NEW date line, the previous one is finished.

                dt_s, rest = m_date.groups()
                dt = datetime.strptime(dt_s, "%d.%m.%Y").date()

                # Check for "Saldo anterior" special case
                if "Saldo anterior" in rest:
                    # Parse balance
                    m_amt = amounts_pattern.search(rest)
                    if m_amt:
                        val_s, sign = m_amt.group(1), m_amt.group(2)
                        amount = self._parse_br_amount(val_s)
                        if sign == 'D':
                            amount = -abs(amount)
                        else:
                            amount = abs(amount)
                        bal_start = amount
                    # Do not create a transaction for Saldo anterior
                    current_txn = None
                    continue

                # Parse regular transaction amounts
                m_amt = amounts_pattern.search(rest)
                if not m_amt:
                    # Maybe amount is on next line? Unlikely for this layout based on samples.
                    # Or maybe it's a header line that looked like a date?
                    current_txn = None
                    continue

                val_s, sign = m_amt.group(1), m_amt.group(2)
                amount = self._parse_br_amount(val_s)
                if sign == 'D':
                    amount = -abs(amount)
                else:
                    amount = abs(amount)

                # Check if there is a second amount (Balance)
                # If present, capture it (could use for verification, or bal_end if it's the last one)
                if m_amt.group(3):
                    bal_s, bal_sign = m_amt.group(3), m_amt.group(4)
                    bal_val = self._parse_br_amount(bal_s)
                    if bal_sign == 'D':
                        bal_val = -abs(bal_val)
                    else:
                        bal_val = abs(bal_val)
                    # We can update bal_end progressively; the last one seen will be the final balance
                    bal_end = bal_val

                # Extract initial description (everything before the amounts)
                # m_amt.start() gives index where amounts begin in 'rest'
                desc_text = rest[:m_amt.start()].strip()

                # Create new transaction object
                current_txn = {
                    'date': dt,
                    'amount': amount,
                    'description': desc_text,
                    'source': 'Bank'
                }
                rows.append(current_txn)

            else:
                # Line does not start with date
                # Check if it's a continuation of the previous transaction
                # Identify if it's a header/footer to ignore
                if any(k in line.upper() for k in ["SALDO", "DATA", "HISTÓRICO", "MOD.", "EXTRATO", "CONTA CORRENTE", "AGÊNCIA", "LIM. ESPECIAL", "BLOQUEADO", "DISPONÍVEL", "CPMF", "VENCIMENTO", "OURO EMPRESARIAL"]):
                    continue

                if current_txn:
                    # Append to description
                    current_txn['description'] += " " + line

        return rows, bal_start, bal_end

    def _has_full_format(self, text):
        """Check if text contains full format transactions (with agência/lote)."""
        lines = text.split('\n')
        import re
        # Look for pattern: DATE + 4-digit-code + 8-digit-code
        full_pattern = re.compile(r'\d{2}/\d{2}/\d{4}\s+\d{4}\s+\d{8}')
        for line in lines[:30]:  # Check first 30 lines
            if full_pattern.search(line):
                return True
        return False
    
    def _extract_full_format(self, page):
        """Extract from BB format with agência/lote codes."""
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        import re
        # Pattern: DATE AGÊNCIA LOTE DESCRIPTION VALOR C/D
        # Example: 05/03/2025 3935 99020870 Transferência recebida 603.935.000.011.535 5.186,00 C
        txn_pattern = re.compile(
            r'(\d{2}/\d{2}/\d{4})\s+(\d{4})\s+(\d{8})\s+(.*?)\s+([\d\.,]+)\s+([CD])'
        )
        
        # Compact format (all on one line, may have truncated date)
        # Pattern: DD/MM/202X LOTE [DOC] DESC VALOR (+/-)
        # Example: 03/01/202 9903 BB Rende Fácil 13.508,56 (-)
        # Amount pattern is specific: ends with ,DD (two decimal digits)
        compact_pattern = re.compile(
            r'(\d{2}/\d{2}/\d{3,4})\s+\d+\s+(?:\d+\s+)?(.*?)\s+([\d\.]+,\d{2})\s*\(([+\-])\)'
        )
        
        last_year = datetime.now().year  # Fallback year
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip headers
            if any(word in line.upper() for word in ['DOCUMENTO', 'DATA', 'LANÇAMENTO']):
                continue
            
            # Try standard full format first
            m = txn_pattern.search(line)
            if m:
                try:
                    dt_s, ag, lote, desc, val_s, sign = m.groups()
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    last_year = dt.year  # Remember year for next truncated date
                    amount = self._parse_br_amount(val_s)
                    if sign == 'D':
                        amount = -abs(amount)
                    else:
                        amount = abs(amount)
                    
                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc.strip(),
                        'source': 'Bank'
                    })
                except:
                    pass
                continue
            
            # Try compact format (often last line with truncated date)
            m_compact = compact_pattern.search(line)
            if m_compact:
                try:
                    dt_s, desc, val_s, sign_char = m_compact.groups()
                    
                    # Handle truncated date: use year from previous transaction
                    if len(dt_s) == 9:  # DD/MM/202
                        dt_s = dt_s + str(last_year)[-1]  # Complete with last digit of previous year
                    
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    last_year = dt.year  # Update for next transaction
                    
                    amount = self._parse_br_amount(val_s)
                    if sign_char == '-':
                        amount = -abs(amount)
                    else:
                        amount = abs(amount)
                    
                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc.strip(),
                        'source': 'Bank'
                    })
                except:
                    pass
        
        # DON'T fall back to generic extraction - return what we found
        return rows, bal_start, bal_end
    
    def _extract_simplified_format(self, page):
        """Extract from simplified BB format where date may be on its own line."""
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        lines = text.split('\n')
        
        import re
        
        # Compact format pattern (for last lines with truncated dates)
        compact_pattern = re.compile(
            r'(\d{2}/\d{2}/\d{3,4})\s+\d+\s+(?:\d+\s+)?(.*?)\s+([\d\.]+,\d{2})\s*\(([+\-])\)'
        )
        last_year = datetime.now().year
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # FIRST: Check for compact format (often last line of page)
            m_compact = compact_pattern.search(line)
            if m_compact:
                try:
                    dt_s, desc, val_s, sign_char = m_compact.groups()
                    
                    # Handle truncated date
                    if len(dt_s) == 9:  # DD/MM/202
                        dt_s = dt_s + str(last_year)[-1]
                    
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    last_year = dt.year
                    
                    amount = self._parse_br_amount(val_s)
                    if sign_char == '-':
                        amount = -abs(amount)
                    else:
                        amount = abs(amount)
                    
                    rows.append({
                        'date': dt,
                        'amount': amount,
                        'description': desc.strip(),
                        'source': 'Bank'
                    })
                    i += 1
                    continue  # Skip remaining checks for this line
                except:
                    pass  # Fall through to other checks
            
            # Check if line is JUST a date (or date + whitespace)
            date_only_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s*$', line)
            if date_only_match:
                # Date is on its own line, transaction details on next line(s)
                dt_s = date_only_match.group(1)
                
                try:
                    dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                    
                    # Look at next few lines for transaction details
                    # Format: LOTE DOCUMENTO DESCRIPTION VALOR (+/-)
                    # Or: DESCRIPTION
                    #     LOTE DOCUMENTO VALOR (+/-)
                    
                    description_parts = []
                    amount = None
                    sign_char = None
                    
                    j = i + 1
                    while j < len(lines) and j < i + 5:  # Look ahead max 5 lines
                        next_line = lines[j].strip()
                        if not next_line:
                            j += 1
                            continue
                        
                        # Stop if we hit another date line
                        if re.match(r'^\d{2}/\d{2}/\d{4}', next_line):
                            break
                        
                        # Look for amount pattern: valor (+) or valor (-)
                        amt_pattern = re.search(r'([\d\.,]+)\s*\(([+\-])\)', next_line)
                        if amt_pattern:
                            val_s, sign_char = amt_pattern.groups()
                            amount = self._parse_br_amount(val_s)
                            # Add the rest of this line to description (before the amount)
                            desc_part = next_line[:amt_pattern.start()].strip()
                            if desc_part:
                                description_parts.append(desc_part)
                            j += 1
                            break  # Found amount, stop looking
                        else:
                            # No amount on this line, it's part of description
                            description_parts.append(next_line)
                        
                        j += 1
                    
                    if amount is not None:
                        if sign_char == '-':
                            amount = -abs(amount)
                        else:
                            amount = abs(amount)
                        
                        description = ' '.join(description_parts).strip()
                        if description:  # Only add if we have a description
                            rows.append({
                                'date': dt,
                                'amount': amount,
                                'description': description,
                                'source': 'Bank'
                            })
                        
                        # Move to the line after the one we consumed
                        i = j
                        continue  # Use continue to skip the i+=1 at end
                except:
                    pass
            
            # Also handle case where date + description are on same line
            else:
                date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.*)', line)
                if date_match:
                    dt_s, rest = date_match.groups()
                    
                    # Skip header lines
                    if any(word in rest.upper() for word in ['DOCUMENTO', 'DATA', 'SALDO', 'AGÊNCIA', 'LANÇAMENTO', 'HISTÓRICO', 'VALOR', 'DIA', 'LOTE']):
                        i += 1
                        continue
                    
                    try:
                        dt = datetime.strptime(dt_s, "%d/%m/%Y").date()
                        
                        # Try to find amount on this line or next
                        # Pattern: valor (+) or (-)
                        amount_pattern = re.compile(r'([\d\.,]+)\s*\(([+\-])\)')
                        
                        # Check current line
                        amt_match = amount_pattern.search(line)
                        description = rest.strip()
                        
                        if not amt_match and i + 1 < len(lines):
                            # Check next line
                            next_line = lines[i + 1].strip()
                            amt_match = amount_pattern.search(next_line)
                            if amt_match:
                                # Amount was on next line, add description parts
                                desc_part = next_line[:amt_match.start()].strip()
                                if desc_part:
                                    description += " " + desc_part
                                
                                # Extract amount and add transaction
                                val_s, sign_char = amt_match.groups()
                                amount = self._parse_br_amount(val_s)
                                if sign_char == '-':
                                    amount = -abs(amount)
                                else:
                                    amount = abs(amount)
                                
                                if description:
                                    rows.append({
                                        'date': dt,
                                        'amount': amount,
                                        'description': description,
                                        'source': 'Bank'
                                    })
                                
                                # Skip both current and next line
                                i += 2
                                continue
                        
                        # Amount was on current line (or not found)
                        if amt_match:
                            val_s, sign_char = amt_match.groups()
                            amount = self._parse_br_amount(val_s)
                            if sign_char == '-':
                                amount = -abs(amount)
                            else:
                                amount = abs(amount)
                            
                            if description:  # Only add if we have a description
                                rows.append({
                                    'date': dt,
                                    'amount': amount,
                                    'description': description,
                                    'source': 'Bank'
                                })
                    except:
                        pass
            
            i += 1
        
        
        # DON'T fall back to generic extraction - return what we found
        return rows, bal_start, bal_end

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
