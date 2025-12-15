"""
Activity Logger

Records user activities for auditing and analytics.
"""
import json
import logging
import streamlit as st
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

# Default log directory
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "activities"


class ActivityLogger:
    """
    Logs user activities to JSON files.
    
    Each user has their own log file: logs/activities/{username}.jsonl
    """
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log(
        self, 
        username: str, 
        action: str, 
        details: Optional[Dict] = None,
        category: str = "general"
    ):
        """
        Log a user activity.
        
        Args:
            username: User who performed the action
            action: Description of the action
            details: Additional details (dict)
            category: Action category (upload, process, export, etc.)
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "username": username,
            "action": action,
            "category": category,
            "details": details or {}
        }
        
        log_file = self.log_dir / f"{username}.jsonl"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
    
    def get_user_activities(
        self, 
        username: str, 
        limit: int = 50
    ) -> List[Dict]:
        """Get recent activities for a user."""
        log_file = self.log_dir / f"{username}.jsonl"
        
        if not log_file.exists():
            return []
        
        activities = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        activities.append(json.loads(line))
        except Exception as e:
            logger.error(f"Failed to read activities: {e}")
            return []
        
        # Return most recent first
        return activities[-limit:][::-1]
    
    def get_all_activities(self, limit: int = 100) -> List[Dict]:
        """Get recent activities from all users (admin only)."""
        all_activities = []
        
        for log_file in self.log_dir.glob("*.jsonl"):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            all_activities.append(json.loads(line))
            except Exception:
                continue
        
        # Sort by timestamp descending
        all_activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return all_activities[:limit]
    
    def get_stats(self, username: Optional[str] = None) -> Dict:
        """Get activity statistics."""
        if username:
            activities = self.get_user_activities(username, limit=1000)
        else:
            activities = self.get_all_activities(limit=1000)
        
        if not activities:
            return {'total': 0, 'by_category': {}, 'by_user': {}}
        
        by_category = {}
        by_user = {}
        
        for a in activities:
            cat = a.get('category', 'general')
            user = a.get('username', 'unknown')
            
            by_category[cat] = by_category.get(cat, 0) + 1
            by_user[user] = by_user.get(user, 0) + 1
        
        return {
            'total': len(activities),
            'by_category': by_category,
            'by_user': by_user
        }


# Global instance
_activity_logger = None


def get_activity_logger() -> ActivityLogger:
    """Get global ActivityLogger instance."""
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ActivityLogger()
    return _activity_logger


def log_activity(action: str, details: Optional[Dict] = None, category: str = "general"):
    """
    Log activity for current user.
    
    Args:
        action: Description of the action
        details: Additional details
        category: Category (upload, process, export, view, etc.)
    """
    username = st.session_state.get('username', 'anonymous')
    get_activity_logger().log(username, action, details, category)


def log_upload(filename: str, file_type: str):
    """Log file upload activity."""
    log_activity(
        f"Upload: {filename}",
        {"filename": filename, "type": file_type},
        category="upload"
    )


def log_process(filename: str, result: str, transactions_count: int = 0):
    """Log file processing activity."""
    log_activity(
        f"Processamento: {filename} → {result}",
        {"filename": filename, "result": result, "transactions": transactions_count},
        category="process"
    )


def log_export(filename: str, format: str):
    """Log file export activity."""
    log_activity(
        f"Export: {filename} ({format})",
        {"filename": filename, "format": format},
        category="export"
    )


def log_view(page: str):
    """Log page view activity."""
    log_activity(f"Visualizou: {page}", {"page": page}, category="view")
