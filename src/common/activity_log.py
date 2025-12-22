"""
Activity Logger for FastAPI Architecture

Records user activities for auditing and analytics in JSONL format.
Integrated with structured logging system.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict
from src.common.logging_config import get_logger

logger = get_logger(__name__)

# Default log directory relative to project root (assuming we are in src/common)
LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "activities"

class ActivityLogger:
    """
    Logs user activities to JSON files.
    
    Logs are stored in logs/activities/session_{date}.jsonl
    """
    
    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or LOG_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log(
        self, 
        action: str, 
        details: Optional[Dict] = None,
        category: str = "general",
        user: str = "system"
    ):
        """
        Log a user activity.
        
        Args:
            action: Description of the action
            details: Additional details (dict)
            category: Action category (upload, process, export, etc.)
            user: Username or session identifier
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "action": action,
            "category": category,
            "details": details or {}
        }
        
        # Log to structured logger as well
        logger.info(
            f"Activity: {action}",
            category=category,
            user=user,
            activity_details=details or {}
        )
        
        # Use a daily log file for general activities
        log_file = self.log_dir / f"activity_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"Failed to log activity: {e}", exc_info=True)

# Global instance
_activity_logger = None

def get_activity_logger() -> ActivityLogger:
    """Get global ActivityLogger instance."""
    global _activity_logger
    if _activity_logger is None:
        _activity_logger = ActivityLogger()
    return _activity_logger

def log_activity(action: str, details: Optional[Dict] = None, category: str = "general", user: str = "anonymous"):
    """Global logging helper."""
    get_activity_logger().log(action, details, category, user)

def log_upload(filename: str, file_type: str, user: str = "anonymous"):
    """Log file upload activity."""
    log_activity(
        f"Upload: {filename}",
        {"filename": filename, "type": file_type},
        category="upload",
        user=user
    )

def log_process(filename: str, result_summary: str, details: Optional[Dict] = None, user: str = "anonymous"):
    """Log reconciliation processing activity."""
    log_activity(
        f"Processamento: {filename} → {result_summary}",
        details or {},
        category="process",
        user=user
    )
