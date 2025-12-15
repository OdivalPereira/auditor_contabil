"""
Admin View

Administrative interface for user management and activity monitoring.
Only accessible to admin users.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from src.cont_ai.auth import get_user_role, require_admin
from src.cont_ai.activity_log import get_activity_logger


def render_admin_view():
    """Render admin panel."""
    if get_user_role() != 'admin':
        st.error("🚫 Acesso restrito a administradores.")
        return
    
    st.header("⚙️ Painel Administrativo")
    
    tab_activities, tab_stats = st.tabs(["📋 Atividades", "📊 Estatísticas"])
    
    with tab_activities:
        render_activities_tab()
    
    with tab_stats:
        render_stats_tab()


def render_activities_tab():
    """Render recent activities table."""
    st.subheader("Atividades Recentes")
    
    logger = get_activity_logger()
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        limit = st.selectbox("Mostrar últimas:", [25, 50, 100, 200], index=1)
    with col2:
        category_filter = st.selectbox(
            "Categoria:", 
            ["Todas", "upload", "process", "export", "view", "general"]
        )
    
    activities = logger.get_all_activities(limit=limit)
    
    if not activities:
        st.info("📭 Nenhuma atividade registrada ainda.")
        return
    
    # Filter by category
    if category_filter != "Todas":
        activities = [a for a in activities if a.get('category') == category_filter]
    
    # Convert to DataFrame
    df = pd.DataFrame(activities)
    
    # Format timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%d/%m %H:%M')
    
    # Rename columns
    df = df.rename(columns={
        'timestamp': 'Data/Hora',
        'username': 'Usuário',
        'action': 'Ação',
        'category': 'Categoria'
    })
    
    # Select columns to show
    columns_to_show = ['Data/Hora', 'Usuário', 'Ação', 'Categoria']
    columns_to_show = [c for c in columns_to_show if c in df.columns]
    
    st.dataframe(
        df[columns_to_show],
        use_container_width=True,
        hide_index=True
    )


def render_stats_tab():
    """Render activity statistics."""
    st.subheader("Estatísticas de Uso")
    
    logger = get_activity_logger()
    stats = logger.get_stats()
    
    if stats['total'] == 0:
        st.info("📭 Sem dados para estatísticas.")
        return
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total de Ações", stats['total'])
    with col2:
        st.metric("Usuários Ativos", len(stats['by_user']))
    with col3:
        most_active = max(stats['by_user'], key=stats['by_user'].get) if stats['by_user'] else '-'
        st.metric("Mais Ativo", most_active)
    
    st.divider()
    
    # By category
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Por Categoria**")
        for cat, count in sorted(stats['by_category'].items(), key=lambda x: -x[1]):
            icon = {
                'upload': '📤',
                'process': '⚙️',
                'export': '📥',
                'view': '👁️',
                'general': '📌'
            }.get(cat, '•')
            st.write(f"{icon} {cat}: **{count}**")
    
    with col2:
        st.markdown("**Por Usuário**")
        for user, count in sorted(stats['by_user'].items(), key=lambda x: -x[1]):
            st.write(f"👤 {user}: **{count}**")
