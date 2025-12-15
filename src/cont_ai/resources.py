"""
Resource Manager

Handles upload limits, file size validation, and resource cleanup.
"""
import os
import logging
import tempfile
import streamlit as st
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, BinaryIO

logger = logging.getLogger(__name__)

# Default configuration
MAX_FILE_SIZE_MB = 50  # Maximum file size in MB
MAX_UPLOADS_PER_SESSION = 20  # Maximum uploads per session
TEMP_DIR = Path(tempfile.gettempdir()) / "contai_temp"


def init_resource_tracking():
    """Initialize resource tracking in session state."""
    if 'upload_count' not in st.session_state:
        st.session_state.upload_count = 0
    if 'total_bytes_processed' not in st.session_state:
        st.session_state.total_bytes_processed = 0


def validate_file_size(file_data: bytes, max_mb: int = MAX_FILE_SIZE_MB) -> tuple[bool, str]:
    """
    Validate file size against limit.
    
    Returns:
        (is_valid, error_message)
    """
    size_mb = len(file_data) / (1024 * 1024)
    
    if size_mb > max_mb:
        return False, f"Arquivo muito grande: {size_mb:.1f}MB (máximo: {max_mb}MB)"
    
    return True, ""


def check_upload_limit(max_uploads: int = MAX_UPLOADS_PER_SESSION) -> tuple[bool, str]:
    """
    Check if user has exceeded upload limit for session.
    
    Returns:
        (can_upload, error_message)
    """
    init_resource_tracking()
    
    if st.session_state.upload_count >= max_uploads:
        return False, f"Limite de uploads atingido ({max_uploads} por sessão)"
    
    return True, ""


def track_upload(file_size: int):
    """Track upload for resource management."""
    init_resource_tracking()
    st.session_state.upload_count += 1
    st.session_state.total_bytes_processed += file_size


def get_resource_stats() -> dict:
    """Get current session resource statistics."""
    init_resource_tracking()
    
    return {
        'uploads': st.session_state.upload_count,
        'max_uploads': MAX_UPLOADS_PER_SESSION,
        'bytes_processed': st.session_state.total_bytes_processed,
        'mb_processed': round(st.session_state.total_bytes_processed / (1024 * 1024), 2)
    }


def cleanup_temp_files(max_age_hours: int = 24):
    """Clean up temporary files older than max_age_hours."""
    if not TEMP_DIR.exists():
        return
    
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    count = 0
    
    for temp_file in TEMP_DIR.glob("*"):
        try:
            mtime = datetime.fromtimestamp(temp_file.stat().st_mtime)
            if mtime < cutoff:
                if temp_file.is_file():
                    temp_file.unlink()
                count += 1
        except Exception:
            pass
    
    if count > 0:
        logger.info(f"Cleaned up {count} temp files")


def save_temp_file(file_data: bytes, filename: str) -> Optional[Path]:
    """Save file to temp directory and return path."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sanitize filename
    safe_name = "".join(c for c in filename if c.isalnum() or c in "._-")
    temp_path = TEMP_DIR / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{safe_name}"
    
    try:
        with open(temp_path, 'wb') as f:
            f.write(file_data)
        return temp_path
    except Exception as e:
        logger.error(f"Failed to save temp file: {e}")
        return None


def render_resource_info():
    """Render resource usage info in sidebar."""
    stats = get_resource_stats()
    
    st.sidebar.caption(f"📤 Uploads: {stats['uploads']}/{stats['max_uploads']}")
    if stats['mb_processed'] > 0:
        st.sidebar.caption(f"💾 Processado: {stats['mb_processed']:.1f}MB")


class ResourceGuard:
    """
    Context manager for resource-safe file processing.
    
    Usage:
        with ResourceGuard(file_data, filename) as guard:
            if guard.is_valid:
                process_file(guard.file_path)
    """
    
    def __init__(self, file_data: bytes, filename: str):
        self.file_data = file_data
        self.filename = filename
        self.file_path = None
        self.is_valid = True
        self.error_message = ""
    
    def __enter__(self):
        # Validate size
        is_valid, msg = validate_file_size(self.file_data)
        if not is_valid:
            self.is_valid = False
            self.error_message = msg
            return self
        
        # Check upload limit
        can_upload, msg = check_upload_limit()
        if not can_upload:
            self.is_valid = False
            self.error_message = msg
            return self
        
        # Save to temp
        self.file_path = save_temp_file(self.file_data, self.filename)
        if self.file_path is None:
            self.is_valid = False
            self.error_message = "Erro ao salvar arquivo temporário"
            return self
        
        # Track upload
        track_upload(len(self.file_data))
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup temp file
        if self.file_path and self.file_path.exists():
            try:
                self.file_path.unlink()
            except Exception:
                pass
        return False
