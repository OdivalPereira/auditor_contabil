"""
Unit Tests for ExtractorPipeline

Tests the PDF extraction pipeline including:
- Layout detection
- Text extraction
- Auto-correction heuristics
- OCR fallback (mocked)
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import from new unified module
from src.parsing.pipeline import ExtractorPipeline
from src.parsing.config.layout import BankLayout, ColumnDef
from src.parsing.config.registry import LayoutRegistry


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_layout():
    """Create a mock BankLayout for testing."""
    return BankLayout(
        name="Test Bank - Monthly",
        bank_id="999",
        keywords=["Test Bank", "Monthly Statement"],
        line_pattern=r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+([\d\.]+,\d{2})\s+([CD])",
        columns=[
            ColumnDef(name="date", match_group=1),
            ColumnDef(name="memo", match_group=2),
            ColumnDef(name="amount", match_group=3),
            ColumnDef(name="type", match_group=4),
        ],
        date_format="%d/%m/%Y",
        amount_decimal_separator=",",
        amount_thousand_separator=".",
    )


@pytest.fixture
def mock_registry(mock_layout):
    """Create a mock LayoutRegistry that returns our test layout."""
    registry = Mock(spec=LayoutRegistry)
    registry.detect = Mock(return_value=mock_layout)
    return registry


@pytest.fixture
def pipeline(mock_registry):
    """Create pipeline with mocked registry."""
    return ExtractorPipeline(mock_registry)


@pytest.fixture
def sample_transactions():
    """Sample transaction dicts for testing."""
    return [
        {
            'date': datetime(2025, 1, 2),
            'memo': 'Payment ABC',
            'amount': -100.00,
            'type': 'DEBIT',
            'fitid': '2025010210000'
        },
        {
            'date': datetime(2025, 1, 3),
            'memo': 'Deposit XYZ',
            'amount': 500.00,
            'type': 'CREDIT',
            'fitid': '2025010350000'
        },
    ]


# ============================================================================
# TEST: INITIALIZATION
# ============================================================================

class TestPipelineInit:
    """Tests for pipeline initialization."""
    
    def test_init_with_registry(self, mock_registry):
        """Should initialize with a registry."""
        pipeline = ExtractorPipeline(mock_registry)
        assert pipeline.registry == mock_registry


# ============================================================================
# TEST: LAYOUT DETECTION
# ============================================================================

class TestLayoutDetection:
    """Tests for layout detection phase."""
    
    @patch('src.parsing.pipeline.pdfplumber')
    def test_layout_detected_successfully(self, mock_pdfplumber, pipeline, mock_layout):
        """Should detect layout and set it in result."""
        # Setup mock PDF
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test Bank Monthly Statement\nSome content"
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        # Mock extractor to return valid data
        with patch('src.parsing.pipeline.GenericPDFExtractor') as MockExtractor:
            mock_extractor = Mock()
            mock_extractor.extract.return_value = {
                'transactions': [],
                'account_info': {},
                'balance_info': {},
                'validation': {'is_valid': True}
            }
            MockExtractor.return_value = mock_extractor
            
            result = pipeline.process_file("test.pdf")
        
        assert result['layout'] == "Test Bank - Monthly"
        pipeline.registry.detect.assert_called_once()
    
    @patch('src.parsing.pipeline.pdfplumber')
    def test_layout_not_detected_returns_error(self, mock_pdfplumber, mock_registry):
        """Should return error when layout not detected."""
        mock_registry.detect.return_value = None
        pipeline = ExtractorPipeline(mock_registry)
        
        mock_page = Mock()
        mock_page.extract_text.return_value = "Unknown bank content with enough text here"
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        result = pipeline.process_file("test.pdf")
        
        assert result['error'] == "Layout not detected in Text mode."
        assert result['layout'] == 'unknown'
    
    @patch('src.parsing.pipeline.pdfplumber')
    def test_pdf_read_error_returns_error(self, mock_pdfplumber, pipeline):
        """Should handle PDF read errors gracefully."""
        mock_pdfplumber.open.side_effect = Exception("Corrupted PDF")
        
        result = pipeline.process_file("corrupted.pdf")
        
        assert "PDF Read Error" in result['error']
        assert result['transactions'] == []


# ============================================================================
# TEST: SIGN FLIP HEURISTIC
# ============================================================================

class TestSignFlipHeuristic:
    """Tests for the sign flip auto-correction heuristic."""
    
    def test_sign_flip_fixes_balance(self, pipeline):
        """Should flip transaction sign when it fixes balance gap."""
        transactions = [
            {'amount': 100.0, 'type': 'CREDIT'},  # Should be -100 (DEBIT)
            {'amount': -50.0, 'type': 'DEBIT'},
        ]
        data = {
            'balance_info': {'start': 1000.0, 'end': 850.0},
            'validation': {'is_valid': False, 'diff': 200.0}
        }
        
        # Gap = 850 - (1000 + 100 - 50) = 850 - 1050 = -200
        # Flipping 100 -> -100: change = -200, matches gap
        
        result = pipeline._try_sign_flip_heuristic(data, transactions)
        
        assert result == True
        assert transactions[0]['amount'] == -100.0
        assert transactions[0]['type'] == 'DEBIT'
        assert data['validation']['is_valid'] == True
    
    def test_sign_flip_no_match(self, pipeline):
        """Should return False when no flip fixes the gap."""
        transactions = [
            {'amount': 100.0, 'type': 'CREDIT'},
            {'amount': -50.0, 'type': 'DEBIT'},
        ]
        data = {
            'balance_info': {'start': 1000.0, 'end': 1000.0},  # No gap that matches
            'validation': {'is_valid': False}
        }
        
        result = pipeline._try_sign_flip_heuristic(data, transactions)
        
        assert result == False
        assert transactions[0]['amount'] == 100.0  # Unchanged
    
    def test_sign_flip_missing_balances(self, pipeline):
        """Should return False when balance info missing."""
        transactions = [{'amount': 100.0, 'type': 'CREDIT'}]
        data = {
            'balance_info': {'start': None, 'end': None},
            'validation': {}
        }
        
        result = pipeline._try_sign_flip_heuristic(data, transactions)
        
        assert result == False


# ============================================================================
# TEST: GHOST RECOVERY HEURISTIC
# ============================================================================

class TestGhostRecoveryHeuristic:
    """Tests for the ghost line recovery heuristic."""
    
    def test_ghost_recovery_fixes_balance(self, pipeline):
        """Should recover discarded transaction when it fixes gap."""
        transactions = [
            {'amount': -100.0, 'type': 'DEBIT'},
        ]
        discarded = [
            {'amount': 50.0, 'type': 'CREDIT', 'memo': 'Ghost line'},
        ]
        data = {
            'balance_info': {'start': 1000.0, 'end': 950.0},
            'validation': {'is_valid': False},
            'discarded_candidates': discarded
        }
        
        # Gap = 950 - (1000 - 100) = 950 - 900 = 50
        # Ghost amount = 50, matches gap
        
        result = pipeline._try_ghost_recovery_heuristic(data, transactions)
        
        assert result == True
        assert len(transactions) == 2
        assert transactions[1]['memo'] == 'Ghost line'
        assert data['validation']['is_valid'] == True
    
    def test_ghost_recovery_no_match(self, pipeline):
        """Should return False when no ghost matches gap."""
        transactions = [{'amount': -100.0, 'type': 'DEBIT'}]
        discarded = [{'amount': 999.0, 'type': 'CREDIT'}]
        data = {
            'balance_info': {'start': 1000.0, 'end': 950.0},
            'validation': {},
            'discarded_candidates': discarded
        }
        
        result = pipeline._try_ghost_recovery_heuristic(data, transactions)
        
        assert result == False
        assert len(transactions) == 1
    
    def test_ghost_recovery_no_discarded(self, pipeline):
        """Should return False when no discarded candidates."""
        transactions = [{'amount': -100.0, 'type': 'DEBIT'}]
        data = {
            'balance_info': {'start': 1000.0, 'end': 950.0},
            'validation': {},
            'discarded_candidates': []
        }
        
        result = pipeline._try_ghost_recovery_heuristic(data, transactions)
        
        assert result == False
    
    def test_ghost_recovery_missing_balances(self, pipeline):
        """Should return False when balance info missing."""
        transactions = []
        data = {
            'balance_info': {'start': None, 'end': 1000.0},
            'discarded_candidates': [{'amount': 50.0}]
        }
        
        result = pipeline._try_ghost_recovery_heuristic(data, transactions)
        
        assert result == False


# ============================================================================
# TEST: FULL PIPELINE FLOW
# ============================================================================

class TestFullPipelineFlow:
    """Integration-style tests for the complete pipeline flow."""
    
    @patch('src.parsing.pipeline.pdfplumber')
    @patch('src.parsing.pipeline.GenericPDFExtractor')
    def test_successful_extraction_text_method(
        self, MockExtractor, mock_pdfplumber, pipeline, sample_transactions
    ):
        """Should successfully extract transactions via text method."""
        # Setup PDF mock
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test Bank Monthly Statement"
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        # Setup extractor mock
        mock_extractor = Mock()
        mock_extractor.extract.return_value = {
            'transactions': sample_transactions,
            'account_info': {'bank_id': '999'},
            'balance_info': {'start': 1000.0, 'end': 1400.0},
            'validation': {'is_valid': True, 'msg': 'OK'}
        }
        MockExtractor.return_value = mock_extractor
        
        # Mock UnifiedTransaction import
        with patch('src.parsing.pipeline.UnifiedTransaction', create=True) as MockUnified:
            MockUnified.side_effect = lambda **kwargs: kwargs
            
            result = pipeline.process_file("statement.pdf")
        
        assert result['method'] == 'Text'
        assert result['layout'] == 'Test Bank - Monthly'
        assert result['error'] is None
        assert len(result['transactions']) == 2
    
    @patch('src.parsing.pipeline.pdfplumber')
    @patch('src.parsing.pipeline.GenericPDFExtractor')
    def test_auto_correction_applied(
        self, MockExtractor, mock_pdfplumber, pipeline
    ):
        """Should apply auto-correction when validation fails."""
        # Setup PDF mock
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test Bank Monthly Statement"
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        # Transaction with wrong sign: should be -100 (DEBIT) but is +100 (CREDIT)
        # Start: 1000, End: 900
        # Current calc: 1000 + 100 = 1100
        # Gap = 900 - 1100 = -200
        # Flip 100 -> -100: potential_change = -2 * 100 = -200
        # Gap (-200) == potential_change (-200) ✓
        bad_transactions = [
            {'date': datetime(2025, 1, 2), 'memo': 'Test', 'amount': 100.0, 'type': 'CREDIT', 'fitid': '123'}
        ]
        
        mock_extractor = Mock()
        mock_extractor.extract.return_value = {
            'transactions': bad_transactions,
            'account_info': {},
            'balance_info': {'start': 1000.0, 'end': 900.0},
            'validation': {'is_valid': False, 'diff': 200.0}
        }
        MockExtractor.return_value = mock_extractor
        
        with patch('src.parsing.pipeline.UnifiedTransaction', create=True) as MockUnified:
            MockUnified.side_effect = lambda **kwargs: kwargs
            
            result = pipeline.process_file("statement.pdf")
        
        assert result['method'] == 'Text (Auto-Corrected)'
        assert 'Corrigido' in result['validation'].get('msg', '')


# ============================================================================
# TEST: EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    @patch('src.parsing.pipeline.pdfplumber')
    def test_empty_pdf(self, mock_pdfplumber, pipeline):
        """Should handle PDF with no pages."""
        mock_pdf = Mock()
        mock_pdf.pages = []
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        # Registry won't detect layout from empty text
        pipeline.registry.detect.return_value = None
        
        result = pipeline.process_file("empty.pdf")
        
        assert result['error'] is not None
    
    @patch('src.parsing.pipeline.pdfplumber')
    @patch('src.parsing.pipeline.GenericPDFExtractor')
    def test_no_transactions_found(
        self, MockExtractor, mock_pdfplumber, pipeline
    ):
        """Should set method to Failed when no transactions found."""
        mock_page = Mock()
        mock_page.extract_text.return_value = "Test Bank Monthly Statement"
        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)
        mock_pdfplumber.open.return_value = mock_pdf
        
        mock_extractor = Mock()
        mock_extractor.extract.return_value = {
            'transactions': [],
            'account_info': {},
            'balance_info': {},
            'validation': {'is_valid': True}
        }
        MockExtractor.return_value = mock_extractor
        
        # Mock OCR to also return empty
        with patch('src.parsing.pipeline.OCRExtractor') as MockOCR:
            mock_ocr = Mock()
            mock_ocr.extract.return_value = {'transactions': [], 'account_info': {}}
            MockOCR.return_value = mock_ocr
            
            with patch('src.parsing.pipeline.UnifiedTransaction', create=True):
                result = pipeline.process_file("no_transactions.pdf")
        
        assert result['method'] == 'Failed'
        assert result['transactions'] == []
