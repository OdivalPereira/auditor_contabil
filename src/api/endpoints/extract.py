from fastapi import APIRouter, File, UploadFile, HTTPException
from typing import List
import os
import tempfile
import shutil
import pandas as pd
from src.parsing.config.registry import LayoutRegistry
from src.parsing.pipeline import ExtractorPipeline
from src.cont_ai.utils.banks import get_bank_name
from src.api.state import global_state

router = APIRouter()

@router.post("/")
async def extract_and_validate(files: List[UploadFile] = File(...)):
    """
    Mirror logic of extractor_app.py:
    Process multiple PDFs, run pipeline, return audit data and transactions.
    """
    # Initialize Pipeline
    root = os.getcwd()
    layouts_dir = os.path.join(root, 'src', 'parsing', 'layouts')
    registry = LayoutRegistry(layouts_dir)
    pipeline = ExtractorPipeline(registry)

    all_raw_transactions = []
    audit_results = []

    for file in files:
        suffix = os.path.splitext(file.filename)[1].lower()
        if suffix != '.pdf':
            audit_results.append({
                "filename": file.filename,
                "status": "error",
                "message": "Somente arquivos PDF são suportados no conversor."
            })
            continue

        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
            
            result = pipeline.process_file(tmp_path)
            
            # Bank Info
            bank_code = result.get('account_info', {}).get('bank_id', '')
            bank_name = get_bank_name(bank_code) if bank_code else "Desconhecido"
            
            # Validation
            validation = result.get('validation', {})
            balances = result.get('balance_info', {})
            
            # Transactions for this file
            txs = result.get('transactions', [])
            tx_count = len(txs)
            
            # Convert UnifiedTransaction to dict
            tx_dicts = [t.to_dict() for t in txs]
            all_raw_transactions.extend(tx_dicts)
            
            audit_results.append({
                "filename": file.filename,
                "status": "success" if validation.get('is_valid') is not False else "warning",
                "bank": f"{bank_name} ({bank_code})" if bank_code else "Não Detectado",
                "tx_count": tx_count,
                "validation": validation,
                "balances": balances,
                "transactions": tx_dicts # Keep file-level transactions if frontend wants to show per-file
            })
            
            os.unlink(tmp_path)
            
        except Exception as e:
            audit_results.append({
                "filename": file.filename,
                "status": "error",
                "message": str(e)
            })

    # Prepare consolidated preview
    df_consolidated = pd.DataFrame(all_raw_transactions)
    if not df_consolidated.empty:
        df_consolidated['source'] = 'Bank_Extractor'
        
    return {
        "audit": audit_results,
        "count": len(all_raw_transactions)
    }

@router.post("/send-to-reconciler")
async def send_to_reconciler(transactions: List[dict]):
    """
    Sets the imported transactions into the global state for the Reconciler tab.
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="Nenhuma transação enviada.")
    
    df = pd.DataFrame(transactions)
    # Standardize types
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    if 'amount' in df.columns:
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
    
    global_state.bank_df = df
    return {"message": f"{len(df)} transações enviadas para Auditoria."}
