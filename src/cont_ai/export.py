"""
Export Module

Multi-format export functionality for transactions.
"""
import csv
import io
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import streamlit as st


def export_to_csv(transactions: List[Dict]) -> str:
    """Export transactions to CSV format."""
    if not transactions:
        return ""
    
    df = pd.DataFrame(transactions)
    return df.to_csv(index=False, sep=';', encoding='utf-8')


def export_to_excel(transactions: List[Dict]) -> bytes:
    """Export transactions to Excel format."""
    if not transactions:
        return b""
    
    df = pd.DataFrame(transactions)
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Transações')
    
    return output.getvalue()


def export_to_json(transactions: List[Dict]) -> str:
    """Export transactions to JSON format."""
    if not transactions:
        return "[]"
    
    # Make serializable
    serializable = []
    for tx in transactions:
        entry = {}
        for key, value in tx.items():
            if isinstance(value, datetime):
                entry[key] = value.isoformat()
            elif hasattr(value, '__dict__'):
                entry[key] = str(value)
            else:
                entry[key] = value
        serializable.append(entry)
    
    return json.dumps(serializable, ensure_ascii=False, indent=2)


def render_export_buttons(transactions: List[Dict], prefix: str = "export"):
    """
    Render multi-format export buttons.
    
    Args:
        transactions: List of transaction dicts
        prefix: Key prefix for buttons
    """
    if not transactions:
        st.warning("Nenhuma transação para exportar.")
        return
    
    st.markdown("**📥 Exportar**")
    
    col1, col2, col3, col4 = st.columns(4)
    
    filename_base = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with col1:
        # CSV
        csv_data = export_to_csv(transactions)
        st.download_button(
            label="📄 CSV",
            data=csv_data,
            file_name=f"transacoes_{filename_base}.csv",
            mime="text/csv",
            key=f"{prefix}_csv"
        )
    
    with col2:
        # Excel
        try:
            excel_data = export_to_excel(transactions)
            st.download_button(
                label="📊 Excel",
                data=excel_data,
                file_name=f"transacoes_{filename_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{prefix}_excel"
            )
        except ImportError:
            st.button("📊 Excel", disabled=True, help="openpyxl não instalado", key=f"{prefix}_excel_disabled")
    
    with col3:
        # JSON
        json_data = export_to_json(transactions)
        st.download_button(
            label="📋 JSON",
            data=json_data,
            file_name=f"transacoes_{filename_base}.json",
            mime="application/json",
            key=f"{prefix}_json"
        )
    
    with col4:
        # OFX (import from existing)
        from src.cont_ai.utils.ofx import OFXWriter
        try:
            # Convert dicts to UnifiedTransaction if needed
            from src.cont_ai.models import UnifiedTransaction
            unified = []
            for tx in transactions:
                if isinstance(tx, dict):
                    unified.append(UnifiedTransaction(
                        date=tx.get('date'),
                        amount=tx.get('amount', 0),
                        memo=tx.get('memo', tx.get('description', '')),
                        type=tx.get('type', 'OTHER'),
                        fitid=tx.get('fitid')
                    ))
                else:
                    unified.append(tx)
            
            writer = OFXWriter()
            ofx_data = writer.generate(unified)
            st.download_button(
                label="💳 OFX",
                data=ofx_data,
                file_name=f"transacoes_{filename_base}.ofx",
                mime="application/x-ofx",
                key=f"{prefix}_ofx"
            )
        except Exception as e:
            st.button("💳 OFX", disabled=True, help=str(e), key=f"{prefix}_ofx_disabled")
