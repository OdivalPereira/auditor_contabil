from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from src.api.state import global_state
from src.exporters.pdf_renderer import PDFReportExporter
import io
import pandas as pd

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
         
    # Prepare dependencies for PDF Exporter
    start_date = results['start_date']
    end_date = results['end_date']
    df_ledger = results['df_ledger']
    df_bank = results['df_bank']
    remaining_l = results['remaining_l']
    remaining_b = results['remaining_b']
    
    pdf_exporter = PDFReportExporter(
        company_name="1266 - MCM FOODS LTDA", # Could be dynamic in future
        start_date=start_date.strftime('%d/%m/%Y') if not df_ledger.empty else None,
        end_date=end_date.strftime('%d/%m/%Y') if not df_ledger.empty else None
    )
    
    # Calc Metrics
    # Note: State might have initial diffs, here we use current remaining.
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
