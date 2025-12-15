"""
Authentication Module

Provides login functionality using streamlit-authenticator.
"""
import yaml
import streamlit as st
import streamlit_authenticator as stauth
from pathlib import Path


def load_auth_config() -> dict:
    """Load authentication configuration from YAML file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "auth.yaml"
    
    if not config_path.exists():
        st.error("⚠️ Arquivo de configuração de autenticação não encontrado!")
        st.stop()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def create_authenticator() -> stauth.Authenticate:
    """Create and return authenticator instance."""
    config = load_auth_config()
    
    authenticator = stauth.Authenticate(
        credentials=config['credentials'],
        cookie_name=config['cookie']['name'],
        cookie_key=config['cookie']['key'],
        cookie_expiry_days=config['cookie']['expiry_days'],
        pre_authorized=config.get('pre-authorized', {}).get('emails', [])
    )
    
    return authenticator


def save_auth_config(config: dict) -> None:
    """Save authentication configuration to YAML file."""
    config_path = Path(__file__).parent.parent.parent / "config" / "auth.yaml"
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False)


def render_login() -> tuple[str, bool, str]:
    """
    Render login form and handle authentication.
    
    Returns:
        tuple: (name, authentication_status, username)
    """
    # Load config here to keep reference
    config = load_auth_config()
    
    authenticator = stauth.Authenticate(
        credentials=config['credentials'],
        cookie_name=config['cookie']['name'],
        cookie_key=config['cookie']['key'],
        cookie_expiry_days=config['cookie']['expiry_days'],
        pre_authorized=config.get('pre-authorized', {}).get('emails', [])
    )
    
    # Login widget
    result = authenticator.login(location='main')
    
    if result is None:
        name = st.session_state.get('name')
        authentication_status = st.session_state.get('authentication_status')
        username = st.session_state.get('username')
    else:
        name, authentication_status, username = result
    
    # Registration Widget (Only show if not logged in)
    if not authentication_status:
        try:
            # register_user(location='main', captcha=False)
            try:
                email_of_registered_user, username_of_registered_user, name_of_registered_user = authenticator.register_user(location='main', captcha=False)
                if email_of_registered_user:
                    # config['credentials'] is updated in-place by register_user
                    save_auth_config(config)
                    st.success('Usuário registrado com sucesso! Faça login acima.')
            except Exception as e:
                st.error(e)
        except Exception as e:
            st.error(f"Erro ao registrar: {e}")

    # Store authenticator in session for logout
    st.session_state['authenticator'] = authenticator
    
    return name, authentication_status, username


def render_logout():
    """Render logout button in sidebar."""
    if 'authenticator' in st.session_state:
        authenticator = st.session_state['authenticator']
        authenticator.logout('Sair', 'sidebar')


def get_user_role() -> str:
    """Get current user's role from config."""
    if 'username' not in st.session_state:
        return 'guest'
    
    config = load_auth_config()
    username = st.session_state.get('username', '')
    
    if username in config['credentials']['usernames']:
        return config['credentials']['usernames'][username].get('role', 'user')
    
    return 'user'


def require_auth(func):
    """Decorator to require authentication for a function."""
    def wrapper(*args, **kwargs):
        if not st.session_state.get('authentication_status'):
            st.warning("⚠️ Faça login para acessar esta funcionalidade.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper


def require_admin(func):
    """Decorator to require admin role."""
    def wrapper(*args, **kwargs):
        if get_user_role() != 'admin':
            st.error("🚫 Acesso restrito a administradores.")
            st.stop()
        return func(*args, **kwargs)
    return wrapper
