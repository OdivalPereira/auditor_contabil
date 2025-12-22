from fastapi import APIRouter, File, UploadFile, HTTPException
from src.api.state import global_state
from src.parsing.sources.ledger_pdf import LedgerParser
from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator
import pandas as pd
import shutil
import os
import tempfile
import traceback

router = APIRouter()

@router.post("/ledger")
async def upload_ledger(file: UploadFile = File(...)):
    try:
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        # Use Legacy LedgerParser which handles both PDF and CSV (delegating to LedgerCSVParser)
        parser = LedgerParser()
        try:
            df = parser.parse(tmp_path)
            # Legacy parser returns clean DataFrame with date (obj), amount (float), description, source
        except Exception as e:
            # If legacy parser fails, raise specific error
            raise ValueError(f"Erro no parser legado: {e}")
        
        if df.empty:
             raise ValueError("Nenhuma transação válida encontrada após processamento (LedgerParser).")

        # Ensure correct types just in case, but respect Parser output
        # Convert date objects to datetime64 for pandas consistency if needed, 
        # but Facade returns .date objects usually. 
        # API State expects datetime64 for matching logic.
        df['date'] = pd.to_datetime(df['date'])
        
        # Store (Accumulate)
        if not global_state.ledger_df.empty:
            global_state.ledger_df = pd.concat([global_state.ledger_df, df], ignore_index=True)
        else:
            global_state.ledger_df = df
            
        global_state.ledger_filename = f"{global_state.ledger_filename}, {file.filename}" if global_state.ledger_filename else file.filename
        
        return {"message": "Ledger uploaded successfully", "count": len(global_state.ledger_df), "filename": file.filename}
        
    except ValueError as ve:
         raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

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
                # Use Legacy Facade which handles OFX and PDF Pipeline
                # Facade.get_parser returns the facade instance itself in current implementation
                facade = ParserFacade.get_parser(tmp_path)
                df, _ = facade.parse(tmp_path)
                
                if df is not None and not df.empty:
                    df['source_file'] = file.filename
                    all_dfs.append(df)
                else:
                    errors.append(f"No transactions found for {file.filename}")
                    
            except Exception as e:
                errors.append(f"Error parsing {file.filename}: {str(e)}")
        
        if all_dfs:
            consolidated = TransactionConsolidator.consolidate(all_dfs)
            # Legacy app filtered small amounts (zeros)
            consolidated = consolidated[abs(consolidated['amount']) > 0.009].copy()
            
            # Ensure dates are datetime (Facade returns date objects)
            consolidated['date'] = pd.to_datetime(consolidated['date'])
            
            # Accumulate
            if not global_state.bank_df.empty:
                global_state.bank_df = pd.concat([global_state.bank_df, consolidated], ignore_index=True)
            else:
                global_state.bank_df = consolidated
            
            return {
                "message": "Bank files processed", 
                "count": len(global_state.bank_df), 
                "errors": errors
            }
        else:
             raise HTTPException(status_code=400, detail=f"No valid transactions. Errors: {errors}")

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clear")
async def clear_data():
    """
    Clears both bank and ledger data from global state.
    """
    global_state.clear()
    return {"message": "Todos os dados foram limpos."}

@router.get("/status")
def get_status():
    return {
        "ledger_count": len(global_state.ledger_df),
        "bank_count": len(global_state.bank_df),
        "ledger_name": global_state.ledger_filename
    }
