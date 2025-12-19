from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse, Response
from src.api.state import global_state
from src.exporters.pdf_renderer import PDFReportExporter
from src.exporting.ofx import OFXWriter
from src.common.models import UnifiedTransaction
import io
import pandas as pd
from typing import List
from datetime import datetime

router = APIRouter()

@router.get("/excel")
def export_excel():
    results = global_state.reconcile_results
    if not results:
        raise HTTPException(status_code=400, detail="No reconciliation data available. Run reconcile first.")
        
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        results['remaining_l'].to_excel(writer, sheet_name='So_no_Diario', index=False)
        results['remaining_b'].to_excel(writer, sheet_name='So_no_Banco', index=False)
        results['matched_l'].to_excel(writer, sheet_name='Conciliados', index=False)
        
    buffer.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="relatorio_conciliacao.xlsx"'
    }
    return StreamingResponse(buffer, media_type='application/vnd.ms-excel', headers=headers)

@router.get("/pdf")
def export_pdf():
    results = global_state.reconcile_results
    if not results:
         raise HTTPException(status_code=400, detail="No reconciliation data available.")
         
    start_date = results['start_date']
    end_date = results['end_date']
    df_ledger = results['df_ledger']
    df_bank = results['df_bank']
    remaining_l = results['remaining_l']
    remaining_b = results['remaining_b']
    
    pdf_exporter = PDFReportExporter(
        company_name="1266 - MCM FOODS LTDA",
        start_date=start_date.strftime('%d/%m/%Y') if not df_ledger.empty else None,
        end_date=end_date.strftime('%d/%m/%Y') if not df_ledger.empty else None
    )
    
    new_diff = abs(remaining_l['amount'].sum() - remaining_b['amount'].sum())
    summary_metrics = {
        'bank_total': df_bank['amount'].sum(),
        'ledger_total': df_ledger['amount'].sum(),
        'net_diff': new_diff,
        'unmatched_bank_count': len(remaining_b),
        'unmatched_ledger_count': len(remaining_l)
    }
    
    try:
        pdf_bytes = pdf_exporter.generate(summary_metrics, remaining_b, remaining_l)
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        
        headers = {
            'Content-Disposition': 'attachment; filename="relatorio_conciliacao.pdf"'
        }
        return StreamingResponse(buffer, media_type='application/pdf', headers=headers)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ofx")
def export_ofx(transactions: List[dict] = Body(...)):
    """
    Export provided transactions as OFX.
    """
    if not transactions:
        raise HTTPException(status_code=400, detail="No transactions provided.")
    
    try:
        # Convert dicts back to UnifiedTransaction if needed, or modify OFXWriter
        # OFXWriter expects List[UnifiedTransaction]
        unified_txs = []
        for t in transactions:
            # Reconstruct date as datetime if it's string
            dt = t.get('date')
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt.replace('Z', ''))
            
            ut = UnifiedTransaction(
                date=dt,
                amount=float(t.get('amount', 0)),
                memo=t.get('memo', t.get('description', '')),
                type=t.get('type', 'OTHER'),
                doc_id=t.get('doc_id', ''),
                fitid=t.get('fitid', '')
            )
            unified_txs.append(ut)
            
        writer = OFXWriter()
        ofx_content = writer.generate(unified_txs)
        
        headers = {
            'Content-Disposition': 'attachment; filename="extrato_exportado.ofx"'
        }
        return Response(content=ofx_content, media_type='application/x-ofx', headers=headers)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
