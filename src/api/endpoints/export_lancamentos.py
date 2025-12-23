"""
Endpoints para exportação de lançamentos contábeis
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from src.api.state import get_session_state
from src.exporters.lancamento_exporter import LancamentoExporter
from src.common.logging_config import get_logger
import pandas as pd
from datetime import datetime
import io

logger = get_logger(__name__)
router = APIRouter()


class TransactionEdit(BaseModel):
    """Modelo para edição de transação"""
    conta_debito: Optional[str] = None
    participante_debito: Optional[str] = ""
    conta_credito: Optional[str] = None
    participante_credito: Optional[str] = ""
    documento: Optional[str] = None


class ManualTransaction(BaseModel):
    """Modelo para transação manual"""
    date: str
    amount: float
    description: str
    conta_debito: str
    participante_debito: Optional[str] = ""
    conta_credito: str
    participante_credito: Optional[str] = ""
    documento: Optional[str] = "001"


class ExportRequest(BaseModel):
    """Modelo para requisição de exportação"""
    selected_ids: List[str]
    company_name: Optional[str] = None
    month: Optional[int] = None
    year: Optional[int] = None
    bank: Optional[str] = "BANCO"


@router.get("/transactions/bank")
def get_bank_transactions(request: Request):
    """Get all bank transactions that can be exported"""
    state = get_session_state(request)
    results = state.reconcile_results
    
    if not results:
        return {"transactions": [], "count": 0}
    
    # Obter transações "apenas no banco"
    remaining_b = results.get('remaining_b', pd.DataFrame())
    
    if remaining_b.empty:
        return {"transactions": [], "count": 0}
    
    # Converter para lista de dicionários
    transactions = []
    for idx, row in remaining_b.iterrows():
        txn_id = f"bank_{idx}"
        
        # Apply any edits from edited_transactions
        edits = state.edited_transactions.get(txn_id, {})
        
        txn = {
            "id": txn_id,
            "date": row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
            "amount": float(row['amount']),
            "description": str(row['description']),
            # Valores padrão ou editados
            "conta_debito": edits.get('conta_debito', '78'),
            "participante_debito": edits.get('participante_debito', ''),
            "conta_credito": edits.get('conta_credito', '6670'),
            "participante_credito": edits.get('participante_credito', ''),
            "documento": edits.get('documento', '001'),
            "bank_name": row.get('bank_account', ''),
            "is_edited": txn_id in state.edited_transactions
        }
        transactions.append(txn)
    
    logger.info(f"Retrieved {len(transactions)} bank-only transactions")
    
    return {
        "transactions": transactions,
        "count": len(transactions)
    }


@router.get("/transactions/manual")
def get_manual_transactions(request: Request):
    """Get all manually added transactions"""
    state = get_session_state(request)
    return {
        "transactions": state.manual_transactions,
        "count": len(state.manual_transactions)
    }


@router.post("/transactions/manual")
def add_manual_transaction(request: Request, transaction: ManualTransaction):
    """Add a new manual transaction"""
    # Generate unique ID for manual transaction
    state = get_session_state(request)
    txn_id = f"manual_{len(state.manual_transactions)}"
    
    txn_dict = {
        "id": txn_id,
        "date": transaction.date,
        "amount": transaction.amount,
        "description": transaction.description,
        "conta_debito": transaction.conta_debito,
        "participante_debito": transaction.participante_debito or "",
        "conta_credito": transaction.conta_credito,
        "participante_credito": transaction.participante_credito or "",
        "documento": transaction.documento or "001",
        "source": "manual",
        "is_edited": False
    }
    
    state.manual_transactions.append(txn_dict)
    
    logger.info(f"Added manual transaction: {txn_id}")
    
    return {
        "success": True,
        "transaction": txn_dict
    }


@router.post("/transactions/edit/{transaction_id}")
def edit_transaction(request: Request, transaction_id: str, edits: TransactionEdit):
    """Edit an existing bank transaction"""
    state = get_session_state(request)
    # Atualizar ou criar dicionário de edições
    if transaction_id not in state.edited_transactions:
        state.edited_transactions[transaction_id] = {}
    
    # Aplicar edições fornecidas
    edit_dict = edits.dict(exclude_unset=True)
    state.edited_transactions[transaction_id].update(edit_dict)
    
    logger.info(f"Updated transaction {transaction_id} with edits: {edit_dict}")
    
    return {
        "message": "Transaction edited successfully",
        "transaction_id": transaction_id,
        "edits": state.edited_transactions[transaction_id]
    }


@router.delete("/transactions/manual/{transaction_id}")
def delete_manual_transaction(request: Request, transaction_id: str):
    """Delete a manual transaction"""
    state = get_session_state(request)
    # Procurar e remover transação
    for i, txn in enumerate(state.manual_transactions):
        if txn['id'] == transaction_id:
            removed = state.manual_transactions.pop(i)
            logger.info(f"Deleted manual transaction: {transaction_id}")
            return {"success": True, "deleted": removed}
    
    raise HTTPException(status_code=404, detail="Transaction not found")


@router.post("/generate")
def generate_export_file(request: Request, request_body: ExportRequest):
    """
    Gera arquivo TXT de exportação com as transações selecionadas.
    """
    state = get_session_state(request)
    # Coletar todas as transações disponíveis
    all_transactions = []
    
    # Transações do banco
    results = state.reconcile_results
    if results:
        remaining_b = results.get('remaining_b', pd.DataFrame())
        if not remaining_b.empty:
            for idx, row in remaining_b.iterrows():
                txn_id = f"bank_{idx}"
                if txn_id in request_body.selected_ids:
                    edits = state.edited_transactions.get(txn_id, {})
                    txn = {
                        "date": row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                        "amount": float(row['amount']),
                        "description": str(row['description']),
                        "conta_debito": edits.get('conta_debito', '78'),
                        "participante_debito": edits.get('participante_debito', ''),
                        "conta_credito": edits.get('conta_credito', '6670'),
                        "participante_credito": edits.get('participante_credito', ''),
                        "documento": edits.get('documento', '001')
                    }
                    all_transactions.append(txn)
    
    # Add manual transactions
    for txn in state.manual_transactions:
        if txn['id'] in request_body.selected_ids:
            all_transactions.append({
                "date": txn['date'],
                "amount": txn['amount'],
                "description": txn['description'],
                "conta_debito": txn['conta_debito'],
                "participante_debito": txn['participante_debito'],
                "conta_credito": txn['conta_credito'],
                "participante_credito": txn['participante_credito'],
                "documento": txn['documento']
            })
    
    if not all_transactions:
        raise HTTPException(status_code=400, detail="No transactions selected")
    
    # Ordenar por data
    all_transactions.sort(key=lambda x: x['date'])
    
    # Gerar conteúdo do arquivo
    exporter = LancamentoExporter()
    
    # Usar dados da requisição    
    # Get company name
    company_name = request_body.company_name or state.company_name
    month = request_body.month or datetime.now().month
    year = request_body.year or datetime.now().year
    bank = request_body.bank or "BANCO"
    
    content = exporter.export_transactions(
        transactions=all_transactions,
        company_name=company_name,
        month=month,
        year=year,
        bank=bank
    )
    
    filename = exporter.generate_filename(company_name, month, year, bank)
    
    logger.info(f"Generated export file with {len(all_transactions)} transactions")
    
    # Retornar arquivo como download
    return Response(
        content=content.encode('utf-8'),
        media_type='text/plain',
        headers={
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    )
