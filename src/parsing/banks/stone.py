import pandas as pd
import pdfplumber
import logging
from ..base import BaseParser

logger = logging.getLogger(__name__)

import re
from datetime import datetime

class StonePDFParser(BaseParser):
    """
    Parser for Stone bank statement PDFs.
    
    Stone Statement Characteristics:
    - **Descending Order**: Newest transactions first (reversed during parsing)
    - **Multi-line Format**: Customer names and payment types appear on separate lines
    - **Tariff Handling**: "Tarifa" entries (including "Débito Tarifa", "Tarifa [Nome]", etc.) 
      are strictly filtered out from the results.
    
    Date-Anchored Extraction:
    ----------------------
    Only lines starting with a date pattern (DD/MM/YYYY or DD/MM/YY) are treated as
    transaction starts. All subsequent non-date lines are concatenated as continuation
    lines (customer names, "Pix | Maquininha", etc.) until the next date line.
    
    This prevents extraction errors like treating "Pix | Maquininha" as a separate
    transaction when it's actually a payment type descriptor.
    
    Tariff Filtering Logic:
    ----------------------
    As requested by the user, all entries containing the word "Tarifa" in their 
    description (or type) are strictly filtered out of the final DataFrame. 
    This ensures that only legitimate movement-based transactions are available 
    for reconciliation.
    
    Vertical Context Handling (Block Identification):
    ---------------------------------------------
    Stone PDFs often split a single transaction into multiple lines:
    1. Line above the date: Often contains the Customer Name.
    2. Date line: Contains amount, type, and transaction balance.
    3. Line below the date: Often contains details like "Pix | Maquininha".
    
    The parser groups these vertically into a single consolidated description:
    "CUSTOMER NAME + TYPE + DETAIL"
    
    Tariffs are treated as standalone blocks to prevent names from other lines
    leaking into them.
    """
    bank_name = 'Stone'

    def parse(self, file_path_or_buffer) -> tuple[pd.DataFrame, dict]:
        df, metadata = self.parse_pdf(file_path_or_buffer)
        
        # Strictly filter out 'Tarifa' entries as requested by the user.
        if not df.empty:
            # Create a mask for rows to keep
            keep_mask = pd.Series(True, index=df.index)
            
            for i in range(len(df)):
                row = df.iloc[i]
                desc_lower = str(row['description']).lower()
                
                # Filter out any entry containing 'tarifa'
                if 'tarifa' in desc_lower:
                    keep_mask.iloc[i] = False
            
            # Apply filter
            df = df[keep_mask].copy()
            
            # Drop the helper balance column if it exists
            if 'balance' in df.columns:
                df = df.drop(columns=['balance'])
        
        # Swap start/end balances and reverse rows for standard reconciliation (Oldest -> Newest)
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)
            
            # Swap balances
            old_start = metadata.get('balance_start')  # This is from FIRST page (31/05 = end)
            old_end = metadata.get('balance_end')  # This is from LAST page (01/05 = after first txn)
            
            # IMPORTANT: old_end is the balance AFTER the first (oldest) transaction
            # To get the true starting balance, we need to reverse that transaction
            first_txn_amount = df.iloc[0]['amount']  # First transaction in chronological order
            true_start = old_end - first_txn_amount  # Reverse the transaction
            
            metadata['balance_start'] = true_start
            metadata['balance_end'] = old_start
            
        return df, metadata

    def extract_page(self, page):
        """
        CONTEXT-AWARE extraction for Stone layouts.
        Strategy:
        1. Identify all lines starting with a date (anchors).
        2. For Credit/Debit sales: Associate name (line above) and detail (line below).
        3. For Tariffs: Keep standalone to prevent name leakage.
        """
        rows = []
        bal_start = None
        bal_end = None
        
        text = page.extract_text() or ""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Date pattern for anchors
        date_pattern = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s')
        
        # Full transaction parsing patterns (robust against IDs/CPF/CNPJ in middle)
        # Pattern 1: has description between type and amounts
        txn_pattern_full = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+(.*?)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$')
        # Pattern 2: amounts follow type immediately
        txn_pattern_short = re.compile(r'^(\d{2}/\d{2}/\d{2,4})\s+(Entrada|Saída|Crédito|Débito|Cr[ée]dito|D[ée]bito)\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})\s+(-?\s*(?:R\$\s*)?[\d\.]+,\d{2})$')

        # Find all anchor indices
        anchors = []
        for idx, line in enumerate(lines):
            if date_pattern.match(line):
                anchors.append(idx)
        
        consumed_lines = set()
        
        for anchor_idx in anchors:
            line = lines[anchor_idx]
            m = txn_pattern_full.search(line)
            if not m:
                m = txn_pattern_short.search(line)
                if not m:
                    continue
                # SHORT format: dt, ttype, val_s, bal_s
                dt_s, ttype, val_s, bal_s = m.groups()
                desc = ""
                # Signs are part of val_s and bal_s in the new regex
            else:
                # FULL format: dt, ttype, desc, val_s, bal_s
                dt_s, ttype, desc, val_s, bal_s = m.groups()
                
            try:
                # Determine transaction type
                is_tariff = 'tarifa' in desc.lower() or 'tarifa' in ttype.lower()
                
                # Group related lines
                block_lines = []
                
                # 1. Look UP for names (only if not a tariff)
                if not is_tariff and anchor_idx > 0:
                    prev_idx = anchor_idx - 1
                    if prev_idx not in anchors and prev_idx not in consumed_lines:
                        # Extra check: names don't usually have digits like balances
                        if not re.search(r'\d{2,},\d{2}', lines[prev_idx]):
                            block_lines.append(lines[prev_idx])
                            consumed_lines.add(prev_idx)
                
                # 2. Add the CORE transaction line
                block_lines.append(line)
                consumed_lines.add(anchor_idx)
                
                # 3. Look DOWN for details (only if not a tariff)
                if not is_tariff and anchor_idx < len(lines) - 1:
                    next_idx = anchor_idx + 1
                    if next_idx not in anchors and next_idx not in consumed_lines:
                        # Details like "Pix | Maquininha"
                        block_lines.append(lines[next_idx])
                        consumed_lines.add(next_idx)

                # --- PARSING THE BLOCK ---
                
                # Date
                fmt = "%d/%m/%Y" if len(dt_s.split('/')[-1]) == 4 else "%d/%m/%y"
                dt = datetime.strptime(dt_s, fmt).date()
                
                # Parse amount (sign is now part of val_s)
                amount = self._parse_br_amount(val_s)
                if ttype.upper() in ['SAÍDA', 'SAIDA', 'DÉBITO', 'DEBITO']:
                    amount = -abs(amount)
                # Note: if it's Crédito but val_s had a minus, _parse_br_amount handles it
                # or we can be explicit if needed, but BR amounts usually have sign at end or start.
                    
                # Description
                # Use clean list of parts, prioritizing Name -> Core Desc -> Detail
                desc_parts = []
                for b_line in block_lines:
                    if b_line == line:
                        # For the anchor line, use only the 'desc' part from regex
                        if desc.strip():
                            desc_parts.append(desc.strip())
                        else:
                            # If no specific desc, use the type (Crédito/Débito)
                            desc_parts.append(ttype.strip())
                    else:
                        desc_parts.append(b_line)
                
                full_desc = " ".join(desc_parts).strip()
                
                # Parse balance (sign is now part of bal_s)
                bal_val = self._parse_br_amount(bal_s)
                    
                rows.append({
                    'date': dt,
                    'amount': amount,
                    'description': full_desc,
                    'source': 'Bank',
                    'balance': bal_val
                })
                
                if bal_start is None:
                    bal_start = bal_val
                bal_end = bal_val
                
            except Exception:
                continue
                
        return rows, bal_start, bal_end
