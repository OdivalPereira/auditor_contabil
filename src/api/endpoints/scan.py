from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.utils.scanner import FileScanner
from src.api.state import global_state
import pandas as pd
import os

router = APIRouter()

class ScanRequest(BaseModel):
    path: str

@router.post("/")
def scan_folder(req: ScanRequest):
    if not os.path.exists(req.path):
        raise HTTPException(status_code=404, detail="Path not found")
        
    try:
        scanner = FileScanner()
        df_scan = scanner.scan_folder(req.path)
        
        # We process this immediately or just return valid files?
        # Returning list of files for user to select is better UX, but for MVP let's auto-ingest or just return list.
        # Frontend will display list.
        
        # Convert DF to records for JSON
        records = df_scan.to_dict(orient='records')
        return {"files": records}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
def ingest_scanned_files(files: list[str]):
    # Ingest specialized logic for locally found files (paths)
    # Similar to upload but reading from disk
    from src.parsing.facade import ParserFacade
    from src.core.consolidator import TransactionConsolidator
    from src.parsing.sources.ofx import OfxParser
    
    all_dfs = []
    errors = []
    
    for file_path in files:
        if not os.path.exists(file_path):
             errors.append(f"Not found: {file_path}")
             continue
             
        try:
            parser = None
            if file_path.lower().endswith('.ofx'):
                 parser = OfxParser()
            else:
                 parser = ParserFacade.get_parser(file_path)
            
            if parser:
                df, _ = parser.parse(file_path)
                df['source_file'] = os.path.basename(file_path)
                all_dfs.append(df)
            else:
                errors.append(f"No parser for {file_path}")
        except Exception as e:
            errors.append(f"Error {file_path}: {e}")
            
    if all_dfs:
        consolidated = TransactionConsolidator.consolidate(all_dfs)
        consolidated = consolidated[abs(consolidated['amount']) > 0.009].copy()
        consolidated['date'] = pd.to_datetime(consolidated['date'])
        
        global_state.bank_df = consolidated
        return {
            "message": "Scanned files ingested",
            "count": len(consolidated),
            "errors": errors
        }
    
    raise HTTPException(status_code=400, detail=f"No valid data. Errors: {errors}")
