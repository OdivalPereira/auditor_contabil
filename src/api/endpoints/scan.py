from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.utils.scanner import FileScanner
from src.api.state import global_state
from src.parsing.facade import ParserFacade
from src.core.consolidator import TransactionConsolidator
import pandas as pd
import os
import tkinter as tk
from tkinter import filedialog
import traceback

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
        
        records = df_scan.to_dict(orient='records')
        return {"files": records}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/browse")
def browse_folder():
    try:
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        # Bring to front hack
        root.lift()
        root.focus_force()
        selected_folder = filedialog.askdirectory(master=root)
        root.destroy()
        
        if selected_folder:
             return {"path": selected_folder}
        return {"path": ""}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error opening dialog: {e}")

@router.post("/ingest")
def ingest_scanned_files(files: list[str]):
    all_dfs = []
    errors = []
    
    for file_path in files:
        if not os.path.exists(file_path):
             errors.append(f"Not found: {file_path}")
             continue
             
        try:
            # Use Legacy Facade EXACTLY like upload_bank
            facade = ParserFacade.get_parser(file_path)
            df, _ = facade.parse(file_path)
            
            if df is not None and not df.empty:
                df['source_file'] = os.path.basename(file_path)
                all_dfs.append(df)
            else:
                errors.append(f"No transactions found for {file_path}")
                
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
