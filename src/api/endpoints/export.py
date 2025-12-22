"""
Endpoints de exportação de relatórios de conciliação.
"""
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import StreamingResponse, Response
from src.api.state import global_state
from src.exporters.pdf_renderer import PDFReportExporter
from src.exporters.excel_exporter import ExcelExporter
from src.exporting.ofx import OFXWriter
from src.common.models import UnifiedTransaction
from src.ui.unified_view import UnifiedViewController
import io
import pandas as pd
from typing import List
from datetime import datetime

router = APIRouter()

@router.post("/excel")
def export_excel(rows_data: List[dict] = Body(...)):
    """Exporta relatório de conciliação em formato Excel moderno com dados filtrados."""
    if not rows_data:
        raise HTTPException(status_code=400, detail="Nenhum dado fornecido para exportação.")
    
    try:
        # Obter informações do período dos dados fornecidos
        dates = [r.get('date') for r in rows_data if r.get('date')]
        if dates:
            start_date = min(dates)
            end_date = max(dates)
            # Converter strings ISO para datetime se necessário
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
            start_str = start_date.strftime('%d/%m/%Y') if pd.notna(start_date) else None
            end_str = end_date.strftime('%d/%m/%Y') if pd.notna(end_date) else None
        else:
            start_str = None
            end_str = None
        
        # Criar exporter
        print(f"DEBUG Excel: company_name = '{global_state.company_name}'")
        exporter = ExcelExporter(
            company_name=global_state.company_name,
            start_date=start_str,
            end_date=end_str
        )
        
        # Gerar Excel
        excel_bytes = exporter.generate(rows_data)
        buffer = io.BytesIO(excel_bytes)
        buffer.seek(0)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        filename = f"conciliacao_{timestamp}.xlsx"
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        return StreamingResponse(
            buffer,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao gerar Excel: {str(e)}")

@router.post("/pdf")
def export_pdf(rows_data: List[dict] = Body(...)):
    """Exporta relatório de conciliação em formato PDF moderno com dados filtrados."""
    if not rows_data:
        raise HTTPException(status_code=400, detail="Nenhum dado fornecido para exportação.")
    
    try:
        # Separar dados por status para as tabelas de discrepância
        conciliados = [r for r in rows_data if 'Conciliado' in r.get('status', '')]
        apenas_banco = [r for r in rows_data if r.get('status') == 'Apenas no Banco']
        apenas_diario = [r for r in rows_data if r.get('status') == 'Apenas no Diário']
        
        # Converter para DataFrames
        df_apenas_banco = pd.DataFrame(apenas_banco)
        df_apenas_diario = pd.DataFrame(apenas_diario)
        
        # Converter datas de string para datetime se necessário
        for df in [df_apenas_banco, df_apenas_diario]:
            if not df.empty and 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
        
        # Obter informações do período
        dates = [r.get('date') for r in rows_data if r.get('date')]
        if dates:
            all_dates = pd.to_datetime(dates)
            start_date = all_dates.min()
            end_date = all_dates.max()
            start_str = start_date.strftime('%d/%m/%Y') if pd.notna(start_date) else None
            end_str = end_date.strftime('%d/%m/%Y') if pd.notna(end_date) else None
        else:
            start_str = None
            end_str = None
        
        # Criar exporter
        print(f"DEBUG PDF: company_name = '{global_state.company_name}'")
        pdf_exporter = PDFReportExporter(
            company_name=global_state.company_name,
            start_date=start_str,
            end_date=end_str
        )
        
        # Calcular métricas
        total_apenas_banco = df_apenas_banco['amount'].sum() if not df_apenas_banco.empty else 0
        total_apenas_diario = df_apenas_diario['amount'].sum() if not df_apenas_diario.empty else 0
        new_diff = abs(total_apenas_diario - total_apenas_banco)
        
        summary_metrics = {
            'bank_total': sum(r.get('amount', 0) for r in rows_data if r.get('source') == 'Banco'),
            'ledger_total': sum(r.get('amount', 0) for r in rows_data if r.get('source') == 'Diário'),
            'net_diff': new_diff,
            'unmatched_bank_count': len(apenas_banco),
            'unmatched_ledger_count': len(apenas_diario)
        }
        
        # Gerar PDF com todas as transações para o resumo
        pdf_bytes = pdf_exporter.generate(
            summary_metrics, 
            df_apenas_banco, 
            df_apenas_diario,
            all_rows=rows_data
        )
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)
        
        # Nome do arquivo com timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        filename = f"conciliacao_{timestamp}.pdf"
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        return StreamingResponse(buffer, media_type='application/pdf', headers=headers)
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PDF: {str(e)}")

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

