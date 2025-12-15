import streamlit as st
from src.cont_ai.auth import render_login, render_logout, get_user_role
from src.cont_ai.session import session_guard, render_session_info
from src.cont_ai.activity_log import log_activity
from src.cont_ai.ui.conciliator_app import render_conciliator_view
from src.cont_ai.ui.extractor_app import render_extractor_view
from src.cont_ai.ui.rule_builder import render_rule_builder
from src.cont_ai.ui.admin_view import render_admin_view

# --- CONFIG ---
st.set_page_config(page_title="Cont.AI - Auditoria Inteligente", layout="wide", page_icon="🤖")

# --- AUTHENTICATION ---
name, authentication_status, username = render_login()

if authentication_status == False:
    st.error('❌ Usuário ou senha incorretos')
    
elif authentication_status == None:
    st.info('👋 Por favor, faça login para continuar')
    
elif authentication_status:
    # --- SESSION MANAGEMENT ---
    session_guard(timeout_minutes=30)
    
    # Log login if first access
    if 'logged_in' not in st.session_state:
        log_activity("Login realizado", category="auth")
        st.session_state.logged_in = True
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown(f"### 👤 {name}")
        st.caption(f"@{username} | {get_user_role().upper()}")
        st.divider()
        render_session_info()
        st.divider()
        render_logout()
    
    # --- HEADER ---
    st.title("🤖 Cont.AI")
    st.markdown("Plataforma Unificada de Inteligência Contábil")

    # --- TABS ---
    # Admin users get an extra tab
    if get_user_role() == 'admin':
        tab_extractor, tab_reconciler, tab_rules, tab_admin = st.tabs([
            "📄 Conversor Inteligente", 
            "⚖️ Auditor Contábil", 
            "🛠️ Construtor de Regras",
            "⚙️ Admin"
        ])
    else:
        tab_extractor, tab_reconciler, tab_rules = st.tabs([
            "📄 Conversor Inteligente", 
            "⚖️ Auditor Contábil", 
            "🛠️ Construtor de Regras"
        ])
        tab_admin = None

    with tab_extractor:
        render_extractor_view()

    with tab_reconciler:
        render_conciliator_view()
        
    with tab_rules:
        render_rule_builder()
    
    if tab_admin:
        with tab_admin:
            render_admin_view()
