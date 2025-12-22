import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd()))

from src.parsing.sources.ledger_csv import LedgerCSVParser

def test_parsing():
    file_path = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil\diarios\CONSULTA DE LANÇAMENTOS DA EMPRESA 1267 - ARRUDA  BARROS LTDA.csv"
    parser = LedgerCSVParser()
    try:
        df = parser.parse(file_path)
        print(f"Success! Extracted {len(df)} transactions.")
        if not df.empty:
            print(f"First row: {df.iloc[0].to_dict()}")
            print(f"Last row: {df.iloc[-1].to_dict()}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_parsing()
