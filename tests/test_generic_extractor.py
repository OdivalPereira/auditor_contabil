"""
Unit tests for GenericPDFExtractor

Tests cover:
- Amount parsing with different separators
- Date parsing with different formats
- Transaction type detection (C/D)
- Line continuation logic
- Balance validation
- Full text extraction flow
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cont_ai.extractor.generic import GenericPDFExtractor
from src.cont_ai.extractor.layout import BankLayout, ColumnDef


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def bb_layout():
    """Fixture for Banco do Brasil monthly statement layout."""
    return BankLayout(
        name="Banco do Brasil - Mensal",
        bank_id="001",
        keywords=["Extrato de Conta", "Conta Corrente", "bb.com.br"],
        line_pattern=r"^(\d{2}\.\d{2}\.\d{4})\s+(.+?)\s+([\d\.]+,\d{2})\s+([CD])",
        columns=[
            ColumnDef(name="date", match_group=1),
            ColumnDef(name="memo", match_group=2),
            ColumnDef(name="amount", match_group=3),
            ColumnDef(name="type", match_group=4),
        ],
        amount_decimal_separator=",",
        amount_thousand_separator=".",
        date_format="%d.%m.%Y",
        has_balance_cleanup=True,
        balance_start_pattern=r"Saldo Anterior.*?([\d\.]+,\d{2})",
        balance_end_pattern=r"Saldo Atual.*?([\d\.]+,\d{2})"
    )


@pytest.fixture
def simple_layout():
    """Fixture for a simple layout without balance patterns."""
    return BankLayout(
        name="Simple Bank",
        bank_id="999",
        keywords=["Simple Bank Statement"],
        line_pattern=r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]+\.\d{2})",
        columns=[
            ColumnDef(name="date", match_group=1),
            ColumnDef(name="memo", match_group=2),
            ColumnDef(name="amount", match_group=3),
        ],
        amount_decimal_separator=".",
        amount_thousand_separator=",",
        date_format="%d/%m/%Y",
        has_balance_cleanup=False
    )


@pytest.fixture
def debit_credit_columns_layout():
    """Fixture for layout with separate debit/credit amount columns."""
    return BankLayout(
        name="Dual Column Bank",
        bank_id="888",
        keywords=["Dual Column"],
        line_pattern=r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d,]*\.?\d*)\s+([\d,]*\.?\d*)",
        columns=[
            ColumnDef(name="date", match_group=1),
            ColumnDef(name="memo", match_group=2),
            ColumnDef(name="amount_debit", match_group=3),
            ColumnDef(name="amount_credit", match_group=4),
        ],
        amount_decimal_separator=".",
        amount_thousand_separator=",",
        date_format="%d/%m/%Y",
        has_balance_cleanup=True
    )


@pytest.fixture
def extractor(bb_layout):
    """Default extractor with BB layout."""
    return GenericPDFExtractor(bb_layout)


@pytest.fixture
def simple_extractor(simple_layout):
    """Extractor with simple layout."""
    return GenericPDFExtractor(simple_layout)


# =============================================================================
# TEST: _parse_amount
# =============================================================================

class TestParseAmount:
    """Tests for amount parsing with different formats."""
    
    def test_parse_brazilian_format(self, extractor):
        """Test parsing Brazilian format: 1.234,56"""
        result = extractor._parse_amount("1.234,56")
        assert result == 1234.56
    
    def test_parse_brazilian_format_no_thousands(self, extractor):
        """Test parsing without thousands separator: 234,56"""
        result = extractor._parse_amount("234,56")
        assert result == 234.56
    
    def test_parse_brazilian_large_number(self, extractor):
        """Test parsing large numbers: 1.234.567,89"""
        result = extractor._parse_amount("1.234.567,89")
        assert result == 1234567.89
    
    def test_parse_us_format(self, simple_extractor):
        """Test parsing US format: 1,234.56"""
        result = simple_extractor._parse_amount("1,234.56")
        assert result == 1234.56
    
    def test_parse_small_amount(self, extractor):
        """Test parsing small amounts: 0,01"""
        result = extractor._parse_amount("0,01")
        assert result == 0.01
    
    def test_parse_zero(self, extractor):
        """Test parsing zero: 0,00"""
        result = extractor._parse_amount("0,00")
        assert result == 0.0


# =============================================================================
# TEST: identify
# =============================================================================

class TestIdentify:
    """Tests for layout identification."""
    
    def test_identify_positive(self, extractor):
        """Test identification with all keywords present."""
        text = "Extrato de Conta Corrente - bb.com.br"
        assert extractor.identify(text) is True
    
    def test_identify_negative_missing_keyword(self, extractor):
        """Test identification with missing keyword."""
        text = "Extrato de Conta - Outro Banco"
        assert extractor.identify(text) is False
    
    def test_identify_negative_empty(self, extractor):
        """Test identification with empty text."""
        assert extractor.identify("") is False


# =============================================================================
# TEST: _is_continuation_line
# =============================================================================

class TestIsContinuationLine:
    """Tests for multiline memo detection."""
    
    def test_valid_continuation(self, extractor):
        """Test valid continuation line."""
        assert extractor._is_continuation_line("Pagamento referente a NF 12345") is True
    
    def test_reject_short_line(self, extractor):
        """Test rejection of very short lines."""
        assert extractor._is_continuation_line("AB") is False
    
    def test_reject_separator_equals(self, extractor):
        """Test rejection of separator lines."""
        assert extractor._is_continuation_line("================") is False
    
    def test_reject_separator_dashes(self, extractor):
        """Test rejection of dash separators."""
        assert extractor._is_continuation_line("-----------------") is False
    
    def test_reject_balance_keyword(self, extractor):
        """Test rejection of balance keywords."""
        assert extractor._is_continuation_line("SALDO ANTERIOR") is False
    
    def test_reject_header_keyword(self, extractor):
        """Test rejection of header keywords."""
        assert extractor._is_continuation_line("EXTRATO MENSAL") is False
    
    def test_reject_page_keyword(self, extractor):
        """Test rejection of page markers."""
        assert extractor._is_continuation_line("PÁGINA 1 DE 3") is False
    
    def test_reject_masked_data(self, extractor):
        """Test rejection of masked data patterns."""
        assert extractor._is_continuation_line("CPF: **/**/****") is False
    
    def test_reject_total_keyword(self, extractor):
        """Test rejection of total/transport keywords."""
        assert extractor._is_continuation_line("A TRANSPORTAR") is False


# =============================================================================
# TEST: _parse_match
# =============================================================================

class TestParseMatch:
    """Tests for regex match parsing."""
    
    def test_parse_debit_transaction(self, extractor):
        """Test parsing a debit transaction."""
        # Simulate regex match
        match = Mock()
        match.groups.return_value = ("15.01.2024", "PIX ENVIADO", "150,00", "D")
        
        result = extractor._parse_match(match)
        
        assert result['date'] == datetime(2024, 1, 15)
        assert result['memo'] == "PIX ENVIADO"
        assert result['amount'] == -150.00
        assert result['type'] == 'DEBIT'
    
    def test_parse_credit_transaction(self, extractor):
        """Test parsing a credit transaction."""
        match = Mock()
        match.groups.return_value = ("20.02.2024", "TED RECEBIDA", "1.500,00", "C")
        
        result = extractor._parse_match(match)
        
        assert result['date'] == datetime(2024, 2, 20)
        assert result['memo'] == "TED RECEBIDA"
        assert result['amount'] == 1500.00
        assert result['type'] == 'CREDIT'
    
    def test_parse_generates_fitid(self, extractor):
        """Test that FITID is generated correctly."""
        match = Mock()
        match.groups.return_value = ("01.03.2024", "TESTE", "100,00", "C")
        
        result = extractor._parse_match(match)
        
        assert 'fitid' in result
        assert result['fitid'].startswith("20240301")


# =============================================================================
# TEST: _validate_consistency
# =============================================================================

class TestValidateConsistency:
    """Tests for balance validation logic."""
    
    def test_valid_balance(self, extractor):
        """Test validation with matching balances."""
        transactions = [
            {'amount': 100.00},
            {'amount': -50.00},
            {'amount': 25.00}
        ]
        balances = {'start': 1000.00, 'end': 1075.00}
        
        result = extractor._validate_consistency(transactions, balances)
        
        assert result['is_valid'] is True
        assert "✅" in result['msg']
    
    def test_invalid_balance(self, extractor):
        """Test validation with mismatched balances."""
        transactions = [
            {'amount': 100.00},
            {'amount': -50.00}
        ]
        balances = {'start': 1000.00, 'end': 1100.00}  # Wrong: should be 1050
        
        result = extractor._validate_consistency(transactions, balances)
        
        assert result['is_valid'] is False
        assert "❌" in result['msg']
        assert 'diff' in result
    
    def test_missing_start_balance(self, extractor):
        """Test validation with missing start balance."""
        transactions = [{'amount': 100.00}]
        balances = {'start': None, 'end': 1100.00}
        
        result = extractor._validate_consistency(transactions, balances)
        
        assert result['is_valid'] is None
        assert "não detectado" in result['msg']
    
    def test_missing_end_balance(self, extractor):
        """Test validation with missing end balance."""
        transactions = [{'amount': 100.00}]
        balances = {'start': 1000.00, 'end': None}
        
        result = extractor._validate_consistency(transactions, balances)
        
        assert result['is_valid'] is None
    
    def test_tolerance_for_rounding(self, extractor):
        """Test that small rounding differences are tolerated."""
        transactions = [{'amount': 100.005}]  # Slight rounding issue
        balances = {'start': 1000.00, 'end': 1100.00}
        
        result = extractor._validate_consistency(transactions, balances)
        
        # Should pass with tolerance of 0.02
        assert result['is_valid'] is True


# =============================================================================
# TEST: extract_from_text (Integration)
# =============================================================================

class TestExtractFromText:
    """Integration tests for full text extraction."""
    
    def test_extract_single_transaction(self, extractor):
        """Test extracting a single transaction from text."""
        text = """Extrato de Conta Corrente
bb.com.br

15.01.2024 PIX ENVIADO FULANO 150,00 D

Saldo Atual: 850,00"""
        
        result = extractor.extract_from_text(text)
        
        assert 'transactions' in result
        assert len(result['transactions']) == 1
        assert result['transactions'][0]['amount'] == -150.00
    
    def test_extract_multiple_transactions(self, extractor):
        """Test extracting multiple transactions."""
        text = """15.01.2024 PIX ENVIADO 100,00 D
16.01.2024 TED RECEBIDA 500,00 C
17.01.2024 PAGAMENTO BOLETO 200,00 D"""
        
        result = extractor.extract_from_text(text)
        
        assert len(result['transactions']) == 3
        assert result['transactions'][0]['amount'] == -100.00
        assert result['transactions'][1]['amount'] == 500.00
        assert result['transactions'][2]['amount'] == -200.00
    
    def test_skip_zero_amount(self, extractor):
        """Test that zero-amount transactions are skipped."""
        text = """15.01.2024 TRANSACAO VALIDA 100,00 D
16.01.2024 TRANSACAO ZERO 0,00 C
17.01.2024 OUTRA VALIDA 50,00 C"""
        
        result = extractor.extract_from_text(text)
        
        assert len(result['transactions']) == 2
    
    def test_skip_saldo_lines(self, extractor):
        """Test that balance lines are filtered out."""
        text = """15.01.2024 TRANSACAO NORMAL 100,00 D
15.01.2024 SALDO DO DIA 1.000,00 C
16.01.2024 OUTRA TRANSACAO 50,00 C"""
        
        result = extractor.extract_from_text(text)
        
        # Only 2 valid transactions, "SALDO" line should be filtered
        assert len(result['transactions']) == 2
        
        # Check discarded candidates
        assert len(result['discarded_candidates']) == 1
    
    def test_multiline_memo(self, extractor):
        """Test that multiline memos are concatenated."""
        text = """15.01.2024 PIX ENVIADO PARA 150,00 D
FULANO DE TAL
CPF FINAL 123
16.01.2024 OUTRA TRANSACAO 50,00 C"""
        
        result = extractor.extract_from_text(text)
        
        assert len(result['transactions']) == 2
        # First transaction should have concatenated memo
        memo = result['transactions'][0]['memo']
        assert "PIX ENVIADO PARA" in memo
        assert "FULANO DE TAL" in memo
    
    def test_account_info_populated(self, extractor):
        """Test that account info is populated from layout."""
        text = "15.01.2024 TRANSACAO 100,00 D"
        
        result = extractor.extract_from_text(text)
        
        assert result['account_info']['bank_id'] == "001"


# =============================================================================
# TEST: _scan_for_balances
# =============================================================================

class TestScanForBalances:
    """Tests for balance scanning."""
    
    def test_scan_finds_balances(self):
        """Test finding start and end balances."""
        layout = BankLayout(
            name="Test",
            bank_id="001",
            keywords=["Test"],
            line_pattern=r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d\.]+,\d{2})",
            columns=[],
            # Patterns must have 2 groups: group(1) = date/prefix, group(2) = amount
            balance_start_pattern=r"(Saldo Anterior)\s+([\d\.]+,\d{2})",
            balance_end_pattern=r"(Saldo Atual)\s+([\d\.]+,\d{2})"
        )
        extractor = GenericPDFExtractor(layout)
        
        text = """Saldo Anterior 1.000,00
Movimentações...
Saldo Atual 1.150,00"""
        
        result = extractor._scan_for_balances(text)
        
        assert result['start'] == 1000.00
        assert result['end'] == 1150.00

    
    def test_scan_no_patterns_defined(self, simple_extractor):
        """Test that empty result when no patterns defined."""
        text = "Saldo Anterior 1.000,00"
        
        result = simple_extractor._scan_for_balances(text)
        
        assert result['start'] is None
        assert result['end'] is None


# =============================================================================
# TEST: Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_text(self, extractor):
        """Test extraction from empty text."""
        result = extractor.extract_from_text("")
        
        assert result['transactions'] == []
        assert result['account_info']['bank_id'] == "001"
    
    def test_no_matching_lines(self, extractor):
        """Test extraction when no lines match pattern."""
        text = """Este é um texto sem transações
Apenas texto comum
Nenhuma linha válida"""
        
        result = extractor.extract_from_text(text)
        
        assert result['transactions'] == []
    
    def test_special_characters_in_memo(self, extractor):
        """Test handling of special characters in memo."""
        text = "15.01.2024 PAGTO REF: NF-123/456 & CIA 100,00 D"
        
        result = extractor.extract_from_text(text)
        
        assert len(result['transactions']) == 1
        assert "/" in result['transactions'][0]['memo']
        assert "&" in result['transactions'][0]['memo']


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
