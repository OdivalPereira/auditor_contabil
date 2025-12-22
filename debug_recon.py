from src.parsing.banks.itau import ItauPDFParser
from src.parsing.banks.stone import StonePDFParser
import pandas as pd

def debug_itau():
    parser = ItauPDFParser()
    f = r"extração_pdfs/pdf_modelos/Extrato Sagrado 10 2025 itau.pdf"
    df, meta = parser.parse(f)
    print(f"File: {f}")
    print(f"Txns: {len(df)}")
    print(f"Meta: {meta}")
    if not df.empty:
        print(df.head())
        total = df['amount'].sum()
        print(f"Sum: {total:.2f}")
        expected = (meta['balance_end'] or 0) - (meta['balance_start'] or 0)
        print(f"Expected diff: {expected:.2f}")
        print(f"Gap: {expected - total:.2f}")

def debug_stone():
    parser = StonePDFParser()
    f = r"extração_pdfs/pdf_modelos/Extrato 05 2025 Stone.pdf"
    df, meta = parser.parse(f)
    print(f"File: {f}")
    print(f"Txns: {len(df)}")
    print(f"Meta: {meta}")
    if not df.empty:
        print(df.head())
        total = df['amount'].sum()
        print(f"Sum: {total:.2f}")
        expected = (meta['balance_end'] or 0) - (meta['balance_start'] or 0)
        print(f"Expected diff: {expected:.2f}")
        print(f"Gap: {expected - total:.2f}")

def debug_sicredi():
    from src.parsing.banks.sicredi import SicrediPDFParser
    parser = SicrediPDFParser()
    f = r"extração_pdfs/pdf_modelos/SICREDI 09 2025.pdf"
    df, meta = parser.parse(f)
    print(f"File: {f}")
    print(f"Txns: {len(df)}")
    print(f"Meta: {meta}")

def debug_bradesco():
    from src.parsing.banks.bradesco import BradescoPDFParser
    parser = BradescoPDFParser()
    f = r"extração_pdfs/pdf_modelos/Bradesco 01 2025.PDF"
    df, meta = parser.parse(f)
    print(f"File: {f}")
    print(f"Txns: {len(df)}")
    print(f"Meta: {meta}")
    if not df.empty:
        print(df.head())
        total = df['amount'].sum()
        print(f"Sum: {total:.2f}")
        expected = (meta['balance_end'] or 0) - (meta['balance_start'] or 0)
        print(f"Expected diff: {expected:.2f}")
        print(f"Gap: {expected - total:.2f}")

def debug_bb():
    from src.parsing.banks.bb import BBMonthlyPDFParser
    parser = BBMonthlyPDFParser()
    f = r"extração_pdfs/pdf_modelos/Extrato BB 11 2025.pdf"
    df, meta = parser.parse(f)
    print(f"File: {f}")
    print(f"Txns: {len(df)}")
    print(f"Meta: {meta}")
    if not df.empty:
        print(df.head())
        total = df['amount'].sum()
        print(f"Sum: {total:.2f}")
        expected = (meta['balance_end'] or 0) - (meta['balance_start'] or 0)
        print(f"Expected diff: {expected:.2f}")
        print(f"Gap: {expected - total:.2f}")

if __name__ == "__main__":
    print("\n--- BANCO DO BRASIL ---")
    try:
        debug_bb()
    except Exception as e:
        print(e)
