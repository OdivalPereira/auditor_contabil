import pandas as pd
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional
import threading

# Session-Based State Management
# Each user session gets its own isolated state
class AppState:
    def __init__(self):
        self.ledger_df: pd.DataFrame = pd.DataFrame()
        self.bank_df: pd.DataFrame = pd.DataFrame()
        self.reconcile_results = {}
        self.ledger_filename = None
        self.company_name = "Empresa"  # Nome padrão
        # Export feature data
        self.manual_transactions = []  # Lista de transações adicionadas manualmente
        self.edited_transactions = {}  # Dicionário de edições {id: dados_editados}
        # Session metadata
        self.last_accessed = datetime.now()
    
    def clear(self):
        self.ledger_df = pd.DataFrame()
        self.bank_df = pd.DataFrame()
        self.reconcile_results = {}
        self.ledger_filename = None
        self.company_name = "Empresa"
        self.manual_transactions = []
        self.edited_transactions = {}
        self.last_accessed = datetime.now()
    
    def touch(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now()


class SessionManager:
    """Manages multiple user sessions with automatic cleanup"""
    
    def __init__(self, session_timeout_hours: int = 4):
        self._sessions: Dict[str, AppState] = {}
        self._lock = threading.Lock()
        self.session_timeout = timedelta(hours=session_timeout_hours)
    
    def get_or_create_session(self, session_id: str) -> AppState:
        """Get existing session or create a new one"""
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = AppState()
            
            state = self._sessions[session_id]
            state.touch()
            return state
    
    def get_session(self, session_id: str) -> Optional[AppState]:
        """Get existing session, return None if not found"""
        with self._lock:
            state = self._sessions.get(session_id)
            if state:
                state.touch()
            return state
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a specific session"""
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False
    
    def cleanup_inactive_sessions(self) -> int:
        """Remove sessions that haven't been accessed within timeout period"""
        with self._lock:
            now = datetime.now()
            inactive_sessions = [
                sid for sid, state in self._sessions.items()
                if now - state.last_accessed > self.session_timeout
            ]
            
            for sid in inactive_sessions:
                del self._sessions[sid]
            
            return len(inactive_sessions)
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        with self._lock:
            return len(self._sessions)
    
    @staticmethod
    def generate_session_id() -> str:
        """Generate a new unique session ID"""
        return str(uuid.uuid4())


# Global Session Manager Instance
session_manager = SessionManager()


# Backward compatibility - deprecated, will be removed
global_state = None  # Set to None to catch any remaining direct usage


# Helper function for endpoints
def get_session_state(request):
    """
    Helper function to get session state from request.
    Import this in endpoints instead of importing from main.py to avoid circular imports.
    
    Args:
        request: FastAPI Request object with session_id in request.state
        
    Returns:
        AppState: The session state for this request
    """
    from src.common.logging_config import get_logger
    logger = get_logger("api.state")
    
    session_id = getattr(request.state, "session_id", None)
    if not session_id:
        # This should not happen if middleware is working correctly
        logger.warning("No session_id found in request.state, creating new session")
        session_id = session_manager.generate_session_id()
    
    return session_manager.get_or_create_session(session_id)
