"""
History Manager

Stores and retrieves processing history for users.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import streamlit as st

logger = logging.getLogger(__name__)

# History storage directory
HISTORY_DIR = Path(__file__).parent.parent.parent / "data" / "history"


class HistoryManager:
    """Manages user processing history."""
    
    def __init__(self, history_dir: Optional[Path] = None):
        self.history_dir = history_dir or HISTORY_DIR
        self.history_dir.mkdir(parents=True, exist_ok=True)
    
    def save_entry(
        self,
        username: str,
        filename: str,
        result_summary: Dict[str, Any],
        category: str = "extraction"
    ):
        """
        Save a history entry.
        
        Args:
            username: User who performed the action
            filename: Processed filename
            result_summary: Summary of results
            category: extraction, reconciliation, export
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "category": category,
            "summary": result_summary
        }
        
        user_file = self.history_dir / f"{username}.jsonl"
        
        try:
            with open(user_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def get_history(
        self,
        username: str,
        limit: int = 50,
        category: Optional[str] = None
    ) -> List[Dict]:
        """Get user's processing history."""
        user_file = self.history_dir / f"{username}.jsonl"
        
        if not user_file.exists():
            return []
        
        entries = []
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        if category is None or entry.get('category') == category:
                            entries.append(entry)
        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            return []
        
        # Return most recent first
        return entries[-limit:][::-1]
    
    def clear_history(self, username: str) -> bool:
        """Clear user's history."""
        user_file = self.history_dir / f"{username}.jsonl"
        
        try:
            if user_file.exists():
                user_file.unlink()
            return True
        except Exception:
            return False


# Global instance
_history_manager = None


def get_history_manager() -> HistoryManager:
    """Get global HistoryManager instance."""
    global _history_manager
    if _history_manager is None:
        _history_manager = HistoryManager()
    return _history_manager


def save_to_history(filename: str, result_summary: Dict[str, Any], category: str = "extraction"):
    """Save entry to current user's history."""
    username = st.session_state.get('username', 'anonymous')
    get_history_manager().save_entry(username, filename, result_summary, category)


def render_history_panel():
    """Render history panel in sidebar or main area."""
    username = st.session_state.get('username', 'anonymous')
    history = get_history_manager().get_history(username, limit=10)
    
    if not history:
        st.info("📭 Nenhum histórico ainda.")
        return
    
    st.markdown("**📜 Histórico Recente**")
    
    for entry in history:
        ts = datetime.fromisoformat(entry['timestamp'])
        time_str = ts.strftime('%d/%m %H:%M')
        filename = entry.get('filename', 'Unknown')
        category = entry.get('category', 'unknown')
        
        icon = {'extraction': '📄', 'reconciliation': '⚖️', 'export': '📥'}.get(category, '•')
        
        with st.expander(f"{icon} {filename} - {time_str}"):
            summary = entry.get('summary', {})
            for key, value in summary.items():
                st.caption(f"**{key}:** {value}")
