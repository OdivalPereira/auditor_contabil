"""
Generic PDF Extractor

Extracts transactions from PDFs using regex patterns defined in BankLayout configurations.
"""
import re
import logging
import pdfplumber
from datetime import datetime
from typing import Dict, Any, List
from ..base import BaseExtractor
from ..config.layout import BankLayout

logger = logging.getLogger(__name__)


class GenericPDFExtractor(BaseExtractor):
    """
    Generic PDF extractor using configurable regex patterns.
    
    Uses BankLayout configuration to parse transactions from PDF text
    with automatic balance validation and multiline memo support.
    """
    
    def __init__(self, layout: BankLayout):
        """
        Initialize extractor with bank layout configuration.
        
        Args:
            layout: BankLayout configuration with regex patterns
        """
        self.layout = layout
        self.line_regex = re.compile(self.layout.line_pattern)

    def identify(self, pdf_text: str) -> bool:
        """Check if this extractor can handle the PDF based on keywords."""
        return all(k in pdf_text for k in self.layout.keywords)

    def extract(self, file_path: str) -> Dict[str, Any]:
        """
        Extract transactions from PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Dict with transactions, account_info, balance_info, validation
        """
        full_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    full_text += t + "\n"
        
        return self.extract_from_text(full_text)

    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Parse transactions from raw text string.
        
        Args:
            text: Extracted PDF text
            
        Returns:
            Dict with transactions, account_info, balance_info, validation
        """
        transactions = []
        account_info = {
            'bank_id': self.layout.bank_id,
            'branch_id': '',
            'acct_id': ''
        }
        
        current_transaction = None
        lines = text.split('\n')
        discarded_candidates = []

        for line in lines:
            # Try to find start of transaction
            match = self.line_regex.match(line)
            if match:
                data = self._parse_match(match)
                
                # Check blocklist
                memo_lower = data.get('memo', '').lower()
                is_blocked = False
                
                if self.layout.has_balance_cleanup:
                    blocklist_lines = ["saldo", "total", "transporte", "transport", "a transportar"]
                    if any(b in memo_lower for b in blocklist_lines):
                        is_blocked = True
                
                # Save blocked items for potential recovery
                if is_blocked and abs(data.get('amount', 0)) > 0.001:
                    discarded_candidates.append(data)
                    continue
                
                # Skip zero amounts
                if abs(data.get('amount', 0)) < 0.001:
                    pass
                else:
                    # Valid transaction - finalize previous if exists
                    if current_transaction:
                        if abs(current_transaction.get('amount', 0)) > 0.001:
                            transactions.append(current_transaction)
                    current_transaction = data
            
            # Multiline memo handling
            elif current_transaction:
                if self._is_continuation_line(line):
                    current_transaction['memo'] += " " + line.strip()
    
        # Append last transaction
        if current_transaction:
            if abs(current_transaction.get('amount', 0)) > 0.001:
                transactions.append(current_transaction)
        
        # Balance verification
        balance_info = self._scan_for_balances(text)
        validation = self._validate_consistency(transactions, balance_info)
                 
        return {
            'transactions': transactions,
            'account_info': account_info,
            'balance_info': balance_info,
            'validation': validation,
            'discarded_candidates': discarded_candidates
        }

    def _scan_for_balances(self, text: str) -> Dict[str, Any]:
        """Scan for start and end balance patterns."""
        info = {'start': None, 'end': None}
        if not self.layout.balance_start_pattern and not self.layout.balance_end_pattern:
            return info
            
        lines = text.split('\n')
        for line in lines:
            # Check Start
            if self.layout.balance_start_pattern and not info['start']:
                m = re.search(self.layout.balance_start_pattern, line, re.IGNORECASE)
                if m:
                    try:
                        val = self._parse_amount(m.group(2))
                        info['start'] = val
                    except: 
                        pass
            
            # Check End
            if self.layout.balance_end_pattern:
                m = re.search(self.layout.balance_end_pattern, line, re.IGNORECASE)
                if m:
                    try:
                        val = self._parse_amount(m.group(2))
                        info['end'] = val
                    except: 
                        pass
        return info

    def _validate_consistency(self, transactions: List[Dict], balances: Dict) -> Dict:
        """Validate that Start + Movements = End."""
        if balances['start'] is None or balances['end'] is None:
            return {'is_valid': None, 'msg': "Saldo Inicial/Final não detectado."}
            
        total_movs = sum(t.get('amount', 0) for t in transactions)
        calculated_end = balances['start'] + total_movs
        
        diff = abs(calculated_end - balances['end'])
        
        if diff < 0.02:
            return {'is_valid': True, 'msg': "Conciliação Perfeita! ✅"}
        else:
            return {
                'is_valid': False, 
                'msg': f"❌ Divergência: Calc: {calculated_end:.2f} | Real: {balances['end']:.2f} | Diff: {diff:.2f}",
                'diff': diff
            }

    def _parse_match(self, match) -> Dict[str, Any]:
        """Map regex groups to fields based on Layout.columns definition."""
        raw_values = match.groups()
        result = {}
        
        for col in self.layout.columns:
            if col.match_group and col.match_group <= len(raw_values):
                val = raw_values[col.match_group - 1]
                
                if val:
                    if col.name == 'amount':
                        result['amount'] = self._parse_amount(val)
                    elif col.name == 'date':
                        result['date'] = datetime.strptime(val, self.layout.date_format)
                    elif col.name == 'type':
                        result['type_raw'] = val
                    else:
                        result[col.name] = val.strip()
        
        # Process type indicator
        if 'type_raw' in result:
            raw = result['type_raw'].strip().upper().replace('(', '').replace(')', '')
            
            if raw in ['D', 'DEB', 'DEBITO', 'DÉBITO', '-', 'DR']:
                if 'amount' in result:
                    result['amount'] = -abs(result['amount'])
            elif raw in ['C', 'CRED', 'CREDITO', 'CRÉDITO', '+', 'CR']:
                if 'amount' in result:
                    result['amount'] = abs(result['amount'])

        # Handle dual debit/credit columns
        if 'amount_debit' in result and result['amount_debit']:
            try:
                val = self._parse_amount(result['amount_debit'])
                if val > 0:
                    result['amount'] = -abs(val)
            except: 
                pass
        
        elif 'amount_credit' in result and result['amount_credit']:
            try:
                val = self._parse_amount(result['amount_credit'])
                if val > 0:
                    result['amount'] = abs(val)
            except: 
                pass
                 
        # Transaction type classification
        t_type = 'DEBIT' if result.get('amount', 0) < 0 else 'CREDIT'
        result['type'] = t_type
        
        # FITID generation
        if 'date' in result and 'amount' in result:
            result['fitid'] = f"{result['date'].strftime('%Y%m%d')}{int(abs(result['amount'])*100)}"
        
        return result

    def _parse_amount(self, val: str) -> float:
        """Parse amount string to float using layout separators."""
        clean = val.replace(
            self.layout.amount_thousand_separator, ''
        ).replace(
            self.layout.amount_decimal_separator, '.'
        )
        return float(clean)

    def _is_continuation_line(self, line: str) -> bool:
        """Determine if line is part of previous transaction's memo."""
        l = line.strip()
        u = l.upper()
        
        if len(l) < 3: 
            return False
        
        if "====" in l or "-----" in l or "_____" in l:
            return False
            
        blocklist = [
            "EXTRATO", "SALDO", "PAGE", "PÁGINA", "CONTINUA", 
            "PERIODO:", "PAG.:", "DATA DOCUMENTO", 
            "COOP CRED", "POUP E INVEST", "AGENCIA:", "CONTA:",
            "TOTAL", "SUJEITO", "AUTENTICAÇÃO", "OUVIDORIA",
            "SAC", "ALÔ", "DEFICIT", "SUPERAVIT",
            "TRANSPORTE", "TRANSPORT",
            "SALDO ANTERIOR", "SALDO ATUAL", "SALDO DO DIA",
            "LANCAMENTOS", "DATA HISTORICO"
        ]
        if any(b in u for b in blocklist): 
            return False

        if "**/**/****" in l: 
            return False
        if l.startswith("..."): 
            return False
        
        return True
