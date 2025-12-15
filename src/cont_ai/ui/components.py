"""
UI Components

Reusable UI components for consistent styling and UX.
"""
import streamlit as st
from typing import Optional, Dict, Any, List
import pandas as pd


def render_page_header(title: str, subtitle: str = "", icon: str = ""):
    """Render consistent page header."""
    if icon:
        st.header(f"{icon} {title}")
    else:
        st.header(title)
    
    if subtitle:
        st.caption(subtitle)


def render_status_card(
    status: str,
    value: str,
    icon: str = "📊",
    color: str = "normal"
):
    """
    Render a status metric card.
    
    Args:
        status: Status label
        value: Status value
        icon: Emoji icon
        color: 'success', 'warning', 'error', or 'normal'
    """
    color_map = {
        'success': '🟢',
        'warning': '🟡', 
        'error': '🔴',
        'normal': '⚪'
    }
    indicator = color_map.get(color, '⚪')
    
    st.markdown(f"""
    <div style="padding: 1rem; border-radius: 0.5rem; background: #f0f2f6;">
        <div style="font-size: 0.8rem; color: #666;">{icon} {status}</div>
        <div style="font-size: 1.2rem; font-weight: bold;">{indicator} {value}</div>
    </div>
    """, unsafe_allow_html=True)


def render_progress_indicator(current: int, total: int, label: str = ""):
    """Render progress with label."""
    progress = current / total if total > 0 else 0
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.progress(progress)
    with col2:
        st.caption(f"{current}/{total} {label}")


def render_file_info_card(filename: str, info: Dict[str, Any]):
    """Render file information card."""
    with st.container():
        st.markdown(f"**📄 {filename}**")
        cols = st.columns(len(info))
        for i, (key, value) in enumerate(info.items()):
            with cols[i]:
                st.metric(key, value)


def render_transaction_preview(
    transactions: List[Dict],
    max_rows: int = 10,
    show_summary: bool = True
):
    """Render transaction table with summary."""
    if not transactions:
        st.info("📭 Nenhuma transação para exibir.")
        return
    
    df = pd.DataFrame(transactions)
    
    if show_summary:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Transações", len(df))
        with col2:
            if 'amount' in df.columns:
                total = df['amount'].sum()
                st.metric("Valor Total", f"R$ {total:,.2f}")
        with col3:
            if 'date' in df.columns:
                st.metric("Período", f"{df['date'].min()} - {df['date'].max()}")
    
    st.dataframe(df.head(max_rows), use_container_width=True, hide_index=True)
    
    if len(df) > max_rows:
        st.caption(f"Mostrando {max_rows} de {len(df)} transações")


def render_action_buttons(actions: List[Dict[str, Any]]):
    """
    Render row of action buttons.
    
    Args:
        actions: List of dicts with 'label', 'key', 'type' (optional), 'icon' (optional)
    """
    cols = st.columns(len(actions))
    results = {}
    
    for i, action in enumerate(actions):
        with cols[i]:
            btn_type = action.get('type', 'secondary')
            icon = action.get('icon', '')
            label = f"{icon} {action['label']}" if icon else action['label']
            
            if st.button(label, key=action['key'], type=btn_type):
                results[action['key']] = True
    
    return results


def render_loading_spinner(message: str = "Processando..."):
    """Render loading spinner with message."""
    return st.spinner(message)


def render_success_message(message: str, details: Optional[str] = None):
    """Render success message with optional details."""
    st.success(message)
    if details:
        st.caption(details)


def render_error_message(message: str, details: Optional[str] = None):
    """Render error message with optional details."""
    st.error(message)
    if details:
        with st.expander("Detalhes do erro"):
            st.code(details)


def render_empty_state(
    message: str = "Nenhum dado disponível",
    icon: str = "📭",
    action_label: Optional[str] = None,
    action_key: Optional[str] = None
):
    """Render empty state with optional action."""
    st.markdown(f"""
    <div style="text-align: center; padding: 3rem; color: #666;">
        <div style="font-size: 3rem;">{icon}</div>
        <div style="margin-top: 1rem;">{message}</div>
    </div>
    """, unsafe_allow_html=True)
    
    if action_label and action_key:
        if st.button(action_label, key=action_key):
            return True
    return False
