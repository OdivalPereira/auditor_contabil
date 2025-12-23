import pandas as pd
from datetime import datetime
from src.parsing.banks.bb import BBMonthlyPDFParser
import unittest
from unittest.mock import MagicMock

# Sample text extracted from the PDF (representative pages)
# Note: I'm combining key parts to simulate the flow
PAGE_1_TEXT = """Extrato de Conta
Conta Corrente
Nome CNPJ Posição Data de emissão
ARRUDA & BARROS LTDA 32.677.538/0001-21 Maio/2025 29.10.2025
Agência (prefixo/dv) GS Conta nº/dv Data da abertura
2936-X 37 49.132-2 22.02.2019
Data Dia Histórico Lote Banco Origem Documento Valor - R$ Saldo - R$
30.04.2025 Saldo anterior 0,00 C
02.05.2025 870-Transferência recebida 99020 3935 603935000011535 504,00 C
02/05 11:47 MILENY DE ALMEIDA ARRUDA
02.05.2025 870-Transferência recebida 99021 612936000050123 445,00 C
02/05 11:39 MCM FOODS LTDA
02.05.2025 830-Dep dinheiro ATM 71233 7810 781071233172930 100,00 C
02/05 17:29 SOP-AV.BANDEIRANTES
Mod. 0.51.291-3 - Jan/2025 - SISBB 25030 - bb.com.br - BB Responde 0800 78 5678 - pvb Folha 1"""

PAGE_MIDDLE_TEXT = """Extrato de Conta
Conta Corrente
Nome Agência (prefixo/dv) GS Conta nº/dv
ARRUDA & BARROS LTDA 2936-X 37 49.132-2
Data Dia Histórico Lote Banco Origem Documento Valor - R$ Saldo - R$
14.05.2025 470-Transferência enviada 99021 611873000132161 5.821,00 D
14/05 13:13 CECILIA AMARILA SOARES
14.05.2025 109-Pagamento de Boleto 13105 51401 1.868,69 D
COPA ENERGIA S.A.
14.05.2025 798-BB Rende Fácil 9903 1.122,95 C 0,00 C
Rende Facil
Mod. 0.51.291-3 - Jan/2025 - SISBB 25030 - bb.com.br - BB Responde 0800 78 5678 - pvb Folha 11"""

PAGE_LAST_TEXT = """Extrato de Conta
Conta Corrente
Nome Agência (prefixo/dv) GS Conta nº/dv
ARRUDA & BARROS LTDA 2936-X 37 49.132-2
Data Dia Histórico Lote Banco Origem Documento Valor - R$ Saldo - R$
30.05.2025 109-Pagamento de Boleto 13105 53001 7.387,20 D
BELLO ALIMENTOS LTDA
30.05.2025 351-BB Rende Fácil 9903 3.692,24 D 0,00 C
Rende Facil
Lim. Especial: OURO EMPRESARIAL
Bloqueado - R$ Disponível - R$ CPMF cobrado - R$ Vencimento Limite - R$
0,00 0,00 C 0,00 31.03.2026 1.000,00
Mod. 0.51.291-3 - Jan/2025 - SISBB 25030 - bb.com.br - BB Responde 0800 78 5678 - pvb Folha 23"""

class TestBBNewLayout(unittest.TestCase):
    def test_parse_mod_051(self):
        # Mock PDF pages
        page1 = MagicMock()
        page1.extract_text.return_value = PAGE_1_TEXT

        page_middle = MagicMock()
        page_middle.extract_text.return_value = PAGE_MIDDLE_TEXT

        page_last = MagicMock()
        page_last.extract_text.return_value = PAGE_LAST_TEXT

        pdf = MagicMock()
        pdf.pages = [page1, page_middle, page_last]

        # Mock Context Manager
        mock_pdf_context = MagicMock()
        mock_pdf_context.__enter__.return_value = pdf
        mock_pdf_context.__exit__.return_value = None

        # Instantiate parser
        parser = BBMonthlyPDFParser()

        # Mock the pdfplumber.open context manager
        with unittest.mock.patch('pdfplumber.open', return_value=mock_pdf_context):
             # We pass a dummy path because we mocked open
            df, metadata = parser.parse("dummy.pdf")

        print("\nExtracted DataFrame:")
        print(df)
        print("\nMetadata:")
        print(metadata)

        # Verification

        # 1. Check Balance
        # balance_start is 0.00 from "30.04.2025 Saldo anterior 0,00 C"
        self.assertEqual(metadata.get('balance_start'), 0.00)

        # balance_end should be 0.00 from last Rende Facil line on last page:
        # "30.05.2025 351-BB Rende Fácil 9903 3.692,24 D 0,00 C"
        self.assertEqual(metadata.get('balance_end'), 0.00)

        # 2. Check specific transactions
        # Page 1:
        # 02.05.2025 Transferência recebida ... 504,00 C
        # Description should contain concatenated parts
        tx1 = df[df['description'].str.contains("603935000011535", na=False)]
        self.assertFalse(tx1.empty, "Transaction 1 not found")
        self.assertEqual(tx1.iloc[0]['amount'], 504.00)
        # Check concatenation of next line
        self.assertIn("MILENY DE ALMEIDA ARRUDA", tx1.iloc[0]['description'])

        # Page Middle:
        # 14.05.2025 470-Transferência enviada ... 5.821,00 D
        tx2 = df[df['description'].str.contains("611873000132161", na=False)]
        self.assertFalse(tx2.empty, "Transaction 2 not found")
        self.assertEqual(tx2.iloc[0]['amount'], -5821.00)
        self.assertIn("CECILIA AMARILA SOARES", tx2.iloc[0]['description'])

        # Page Last:
        # 30.05.2025 109-Pagamento de Boleto ... 7.387,20 D
        tx3 = df[df['description'].str.contains("53001", na=False)]
        self.assertFalse(tx3.empty, "Transaction 3 not found")
        self.assertEqual(tx3.iloc[0]['amount'], -7387.20)
        self.assertIn("BELLO ALIMENTOS LTDA", tx3.iloc[0]['description'])

if __name__ == '__main__':
    unittest.main()
