import re
from typing import Dict, Any, List
from ..extractors.generic import GenericPDFExtractor
from ..config.layout import BankLayout

class CresolParser(GenericPDFExtractor):
    """
    Parser específico para Cresol que lida com descrições na linha anterior.
    """
    
    def extract_from_text(self, text: str) -> Dict[str, Any]:
        transactions = []
        account_info = {
            'bank_id': self.layout.bank_id,
            'branch_id': '',
            'acct_id': ''
        }
        
        lines = text.split('\n')
        previous_line = ""
        discarded = []
        
        # Regex patterns
        line_regex = re.compile(self.layout.line_pattern)
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for transaction match
            match = line_regex.match(line)
            if match:
                data = self._parse_match(match)
                
                # Use previous line as memo if available and looks robust
                if previous_line and not self._is_header_garbage(previous_line):
                    data['memo'] = previous_line
                else:
                    data['memo'] = "Descrição não capturada"
                
                # Validation logic same as generic
                if abs(data.get('amount', 0)) > 0.001:
                    transactions.append(data)
                
                # Reset previous line to avoid reuse
                previous_line = ""
            else:
                # If not a transaction line, it might be a description for the NEXT transaction
                # But typically in Cresol PDF observed:
                # LINE 1: PAGAMENTO DE TÍTULOS ...
                # LINE 2: 30/09/2025 ...
                previous_line = line
        
        balance_info = self._scan_for_balances(text)
        validation = self._validate_consistency(transactions, balance_info)
        
        return {
            'transactions': transactions,
            'account_info': account_info,
            'balance_info': balance_info,
            'validation': validation,
            'discarded_candidates': discarded
        }

    def _is_header_garbage(self, line: str) -> bool:
        """Filter out common header lines that shouldn't be used as memo."""
        garbage = [
            "Lançamentos", "Saldo em Conta", "Limite de Crédito",
            "Saldo Disponível", "Data", "Histórico", "Valor",
            "Extrato", "Página", "Saldo do Dia"
        ]
        return any(g.lower() in line.lower() for g in garbage)
