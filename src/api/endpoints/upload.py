from fastapi import APIRouter, File, UploadFile, HTTPException
from src.api.state import global_state
from src.parsing.sources.ledger_pdf import LedgerParser
from src.parsing.sources.ofx import OfxParser
from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator
import pandas as pd
import shutil
import os
import tempfile

router = APIRouter()

@router.post("/ledger")
async def upload_ledger(file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Process Ledger
        # Assuming LedgerParser works with file path or stream if modified, 
        # but existing code uses path in some places.
        # Let's check LedgerParser usage in existing code.
        # It takes 'ledger_file' which can be UploadedFile (Streamlit) or path?
        # In current conciliator_app.py: df_ledger = ledger_parser.parse(ledger_file)
        # If it's a PDF path, LedgerParser handles it.
        
        ledger_parser = LedgerParser()
        if suffix.lower() == '.csv':
            df = pd.read_csv(tmp_path)
        else:
            df = ledger_parser.parse(tmp_path)
            
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce').fillna(0.0)
        df['date'] = pd.to_datetime(df['date'])
        
        global_state.ledger_df = df
        global_state.ledger_filename = file.filename
        
        return {"message": "Ledger uploaded successfully", "count": len(df), "filename": file.filename}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/bank")
async def upload_bank(files: list[UploadFile] = File(...)):
    try:
        all_dfs = []
        errors = []
        
        for file in files:
            suffix = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
            
            try:
                parser = None
                if suffix == '.ofx':
                    parser = OfxParser()
                else:
                    parser = ParserFacade.get_parser(tmp_path)
                
                if parser:
                    df, _ = parser.parse(tmp_path)
                    df['source_file'] = file.filename
                    all_dfs.append(df)
                else:
                    errors.append(f"No parser for {file.filename}")
            except Exception as e:
                errors.append(f"Error parsing {file.filename}: {str(e)}")
        
        if all_dfs:
            consolidated = TransactionConsolidator.consolidate(all_dfs)
            # Filter zeros like in legacy
            consolidated = consolidated[abs(consolidated['amount']) > 0.009].copy()
            consolidated['date'] = pd.to_datetime(consolidated['date'])
            
            # Store in state
            # If bank data already exists, maybe append? For now, replace.
            global_state.bank_df = consolidated
            
            return {
                "message": "Bank files processed", 
                "count": len(consolidated), 
                "errors": errors
            }
        else:
             raise HTTPException(status_code=400, detail=f"No valid transactions found. Errors: {errors}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_status():
    return {
        "ledger_count": len(global_state.ledger_df),
        "bank_count": len(global_state.bank_df),
        "ledger_name": global_state.ledger_filename
    }
