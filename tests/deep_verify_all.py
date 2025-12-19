
import os
import pandas as pd
import sys
import logging
from decimal import Decimal

# Setup paths
ROOT = r"c:\Users\contabil\Documents\Projetos Antigravity\auditor_contabil"
sys.path.append(ROOT)

from src.parsing.pipeline import ExtractorPipeline
from src.parsing.config.registry import LayoutRegistry

def clean_desc(d):
    return " ".join(str(d).split()).upper()

def verify_file(pipeline, bank_name, file_path):
    if not os.path.exists(file_path):
        return {"bank": bank_name, "error": f"File not found: {file_path}"}

    print(f"\n>>> Verifying [{bank_name}] : {os.path.basename(file_path)}")
    
    try:
        result = pipeline.process_file(file_path)
        txns = result.get('transactions', [])
        bal_info = result.get('balance_info', {})
        
        df = pd.DataFrame([t.to_dict() if hasattr(t, 'to_dict') else t for t in txns])
        
        if df.empty:
            return {"bank": bank_name, "file": os.path.basename(file_path), "txns": 0, "status": "FAIL (No transactions)"}
        
        # 1. Check Duplicates
        desc_col = 'memo' if 'memo' in df.columns else 'description'
        df['clean_desc'] = df[desc_col].apply(clean_desc)
        duplicates = df[df.duplicated(subset=['date', 'amount', 'clean_desc'], keep=False)]
        num_dupes = len(duplicates)
        
        # 2. Balance Reconciliation
        bal_start = bal_info.get('start')
        bal_end = bal_info.get('end')
        
        sum_txns = df['amount'].sum()
        reconciled = False
        discrepancy = None
        
        if bal_start is not None and bal_end is not None:
             expected_end = float(bal_start) + float(sum_txns)
             discrepancy = round(float(bal_end) - expected_end, 2)
             if abs(discrepancy) < 0.05: # Allow small float noise
                 reconciled = True
                 
        return {
            "bank": bank_name,
            "file": os.path.basename(file_path),
            "txns": len(df),
            "duplicates": num_dupes,
            "bal_start": bal_start,
            "bal_end": bal_end,
            "sum_txns": round(sum_txns, 2),
            "discrepancy": discrepancy,
            "reconciled": reconciled,
            "status": "PASS" if reconciled else "CHECK (Bal mismatch or no info)"
        }
        
    except Exception as e:
        return {"bank": bank_name, "file": os.path.basename(file_path), "error": str(e), "status": "ERROR"}

def main():
    logging.getLogger('pdfminer').setLevel(logging.ERROR)
    logging.getLogger('pdfplumber').setLevel(logging.ERROR)
    
    registry = LayoutRegistry(os.path.join(ROOT, "src/parsing/layouts"))
    pipeline = ExtractorPipeline(registry)
    
    models_dir = os.path.join(ROOT, "extração_pdfs/pdf_modelos")
    extratos_dir = os.path.join(ROOT, "extratos")
    
    test_cases = [
        ("BB", os.path.join(extratos_dir, "01 2025/Extrato BB 01 2025.pdf")),
        ("BB", os.path.join(models_dir, "Extrato BB 11 2025.pdf")),
        ("BB", os.path.join(models_dir, "BB 06 2025.pdf")),
        ("BB", os.path.join(models_dir, "extrato bb mes 8.pdf")),
        ("BB", os.path.join(models_dir, "Sagrado maio25 bb.pdf")),
        ("Itau", os.path.join(models_dir, "Extrato Sagrado 10 2025 itau.pdf")),
        ("Itau", os.path.join(models_dir, "extrato_itau_02_25.pdf")),
        ("Itau", os.path.join(models_dir, "extrato_itau_03_25.pdf")),
        ("CEF", os.path.join(models_dir, "Extrato CEF.pdf")),
        ("CEF", os.path.join(models_dir, "CEF.pdf")),
        ("Santander", os.path.join(models_dir, "Extrato Santander.pdf")),
        ("Santander", os.path.join(models_dir, "Santander 09.2025.pdf")),
        ("Santander", os.path.join(models_dir, "Santander-11.2025.pdf")),
        ("Stone", os.path.join(models_dir, "Extrato 05 2025 Stone.pdf")),
        ("Sicredi", os.path.join(models_dir, "Extrato Sicredi  Janeiro 2025.pdf")),
        ("Sicredi", os.path.join(models_dir, "SICREDI 09 2025.pdf")),
        ("Sicredi", os.path.join(models_dir, "Extrato Sicredi - Julho 2025.pdf")),
        ("Sicredi", os.path.join(models_dir, "maio25 sicredi.pdf")),
        ("Bradesco", os.path.join(models_dir, "BANCO BRADESCO MODELO 07-25.PDF")),
        ("Bradesco", os.path.join(models_dir, "Bradesco 01 2025.PDF")),
        ("Bradesco", os.path.join(models_dir, "BRADESCO 10 2024.PDF")),
        ("Bradesco", os.path.join(models_dir, "EXTRATO BRADESCO MODELO AGOSTO-2025.PDF")),
        ("Sicoob", os.path.join(models_dir, "Extrato Sicoob 10.2025.pdf")),
        ("Sicoob", os.path.join(models_dir, "Extrato Sicoob 10.2025 2.pdf")),
        ("Sicoob", os.path.join(models_dir, "Extrato Sicoob.pdf"))
    ]
    
    results = []
    for bank, path in test_cases:
        res = verify_file(pipeline, bank, path)
        results.append(res)
        
    print("\n" + "="*140)
    print(f"{'BANK':<12} | {'FILE':<35} | {'TXNS':<5} | {'DUPES':<5} | {'RECON':<8} | {'BAL_START':<12} | {'BAL_END':<12} | {'STATUS'}")
    print("-" * 145)
    
    for r in results:
        if "error" in r:
            print(f"{r.get('bank', 'N/A'):<12} | {r.get('file', 'N/A'):<35} | {'N/A':<5} | {'N/A':<5} | {'N/A':<8} | {'N/A':<12} | {'N/A':<12} | ERROR: {r['error']}")
        else:
            recon_str = "YES" if r.get('reconciled') else "NO"
            bal_start = f"{r.get('bal_start'):.2f}" if r.get('bal_start') is not None else "N/A"
            bal_end = f"{r.get('bal_end'):.2f}" if r.get('bal_end') is not None else "N/A"
            print(f"{r.get('bank', 'N/A'):<12} | {r.get('file', 'N/A'):<35} | {r.get('txns', 0):<5} | {r.get('duplicates', 0):<5} | {recon_str:<8} | {bal_start:<12} | {bal_end:<12} | {r.get('status', 'ERROR')}")

if __name__ == "__main__":
    main()
