"""
Session Manager

Handles session timeout, user tracking, and session state management.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional


# Default configuration
DEFAULT_TIMEOUT_MINUTES = 30
DEFAULT_MAX_SESSIONS_PER_USER = 3


def init_session():
    """Initialize session state with tracking data."""
    if 'session_start' not in st.session_state:
        st.session_state.session_start = datetime.now()
    
    if 'last_activity' not in st.session_state:
        st.session_state.last_activity = datetime.now()
    
    if 'page_views' not in st.session_state:
        st.session_state.page_views = 0


def update_activity():
    """Update last activity timestamp."""
    st.session_state.last_activity = datetime.now()
    st.session_state.page_views = st.session_state.get('page_views', 0) + 1


def check_timeout(timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES) -> bool:
    """
    Check if session has timed out.
    
    Args:
        timeout_minutes: Session timeout in minutes
        
    Returns:
        True if session timed out, False otherwise
    """
    if 'last_activity' not in st.session_state:
        return False
    
    last_activity = st.session_state.last_activity
    timeout_delta = timedelta(minutes=timeout_minutes)
    
    if datetime.now() - last_activity > timeout_delta:
        return True
    
    return False


def force_logout():
    """Force logout by clearing session state."""
    keys_to_keep = ['_is_running']
    keys_to_remove = [k for k in st.session_state.keys() if k not in keys_to_keep]
    
    for key in keys_to_remove:
        del st.session_state[key]


def get_session_info() -> dict:
    """Get current session information."""
    return {
        'start': st.session_state.get('session_start'),
        'last_activity': st.session_state.get('last_activity'),
        'page_views': st.session_state.get('page_views', 0),
        'username': st.session_state.get('username', 'guest'),
        'duration': _get_session_duration()
    }


def _get_session_duration() -> Optional[str]:
    """Get human-readable session duration."""
    if 'session_start' not in st.session_state:
        return None
    
    duration = datetime.now() - st.session_state.session_start
    minutes = int(duration.total_seconds() // 60)
    
    if minutes < 60:
        return f"{minutes}min"
    else:
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours}h {mins}min"


def render_session_info():
    """Render session info in sidebar."""
    info = get_session_info()
    
    if info['duration']:
        st.sidebar.caption(f"⏱️ Sessão: {info['duration']}")
    
    if info['page_views'] > 0:
        st.sidebar.caption(f"📄 Ações: {info['page_views']}")


def session_guard(timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES):
    """
    Guard function to check session validity.
    
    Call at the start of protected pages to enforce timeout.
    """
    init_session()
    
    if check_timeout(timeout_minutes):
        st.warning("⏰ Sua sessão expirou por inatividade.")
        force_logout()
        st.rerun()
    
    update_activity()
