from fastapi import APIRouter, File, UploadFile, HTTPException, Request
from src.api.state import get_session_state
from src.parsing.sources.ledger_pdf import LedgerParser
from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator
from src.common.logging_config import get_logger
import pandas as pd
import shutil
import os
import tempfile
import traceback

logger = get_logger(__name__)
router = APIRouter()

@router.post("/ledger")
async def upload_ledger(request: Request, file: UploadFile = File(...)):
    try:
        logger.info(f"Ledger upload started: {file.filename}")
        suffix = os.path.splitext(file.filename)[1].lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        
        parser = LedgerParser()
        try:
            result = parser.parse(tmp_path)
            # Check if result is a tuple (df, company_name) or just df
            state = get_session_state(request)
            if isinstance(result, tuple):
                df, company_name = result
                state.company_name = company_name
                logger.info("Company name extracted from ledger.", company=company_name)
            else:
                df = result
                logger.info("Ledger parsed (no company name extracted).")
            
            logger.info("Ledger parsed successfully.", tx_count=len(df), format=suffix)
        except Exception as e:
            logger.error(f"Ledger parsing error: {e}", exc_info=True)
            raise ValueError(f"Erro no parser legado: {e}")
        
        if df.empty:
             logger.warning("No valid transactions found in ledger.")
             raise ValueError("Nenhuma transação válida encontrada após processamento (LedgerParser).")

        df['date'] = pd.to_datetime(df['date'])
        
        state = get_session_state(request)
        if not state.ledger_df.empty:
            state.ledger_df = pd.concat([state.ledger_df, df], ignore_index=True)
        else:
            state.ledger_df = df
            
        state.ledger_filename = f"{state.ledger_filename}, {file.filename}" if state.ledger_filename else file.filename
        
        logger.info(f"Ledger updated: {file.filename}", total_count=len(state.ledger_df), file_type="ledger", company=state.company_name)
        return {"message": "Ledger uploaded successfully", "count": len(state.ledger_df), "filename": file.filename, "company": state.company_name}
        
    except ValueError as ve:
         logger.warning(f"Ledger upload validation error: {ve}")
         raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Internal error during ledger upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.post("/bank")
async def upload_bank(request: Request, files: list[UploadFile] = File(...)):
    try:
        logger.info(f"Bank upload started: {len(files)} files")
        all_dfs = []
        errors = []
        
        for file in files:
            logger.debug(f"Processing bank file: {file.filename}")
            suffix = os.path.splitext(file.filename)[1].lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                shutil.copyfileobj(file.file, tmp)
                tmp_path = tmp.name
            
            try:
                facade = ParserFacade.get_parser(tmp_path)
                df, _ = facade.parse(tmp_path)
                
                if df is not None and not df.empty:
                    logger.info(f"File {file.filename} parsed successfully.", tx_count=len(df))
                    df['source_file'] = file.filename
                    all_dfs.append(df)
                else:
                    logger.warning(f"No transactions found in {file.filename}")
                    errors.append(f"No transactions found for {file.filename}")
                    
            except Exception as e:
                logger.error(f"Error parsing {file.filename}: {e}", exc_info=True)
                errors.append(f"Error parsing {file.filename}: {str(e)}")
        
        if all_dfs:
            consolidated = TransactionConsolidator.consolidate(all_dfs)
            consolidated = consolidated[abs(consolidated['amount']) > 0.009].copy()
            consolidated['date'] = pd.to_datetime(consolidated['date'])
            
            state = get_session_state(request)
            if not state.bank_df.empty:
                state.bank_df = pd.concat([state.bank_df, consolidated], ignore_index=True)
            else:
                state.bank_df = consolidated
            
            logger.info("Bank data accumulated successfully.", total_count=len(state.bank_df), files_count=len(files))
            return {
                "message": "Bank files processed", 
                "count": len(state.bank_df), 
                "errors": errors
            }
        else:
             logger.error("Bank upload failed: no valid data extracted.")
             raise HTTPException(status_code=400, detail=f"No valid transactions. Errors: {errors}")

    except Exception as e:
        if not isinstance(e, HTTPException):
            logger.error(f"Internal error during bank upload: {e}", exc_info=True)
        raise e

@router.post("/clear")
async def clear_data(request: Request):
    """
    Clears both bank and ledger data from session state.
    """
    state = get_session_state(request)
    state.clear()
    return {"message": "Todos os dados foram limpos."}

@router.get("/status")
def get_status(request: Request):
    state = get_session_state(request)
    return {
        "ledger_count": len(state.ledger_df),
        "bank_count": len(state.bank_df),
        "ledger_name": state.ledger_filename
    }
