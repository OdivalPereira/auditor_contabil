"""
Processing Cache

Caches PDF processing results to avoid reprocessing identical files.
Uses file hash as cache key.
"""
import hashlib
import json
import logging
import streamlit as st
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, BinaryIO

logger = logging.getLogger(__name__)

# Default cache configuration
CACHE_DIR = Path(__file__).parent.parent.parent / "cache" / "processed"
DEFAULT_TTL_HOURS = 24  # Cache expires after 24 hours


def get_file_hash(file_data: bytes) -> str:
    """Calculate SHA256 hash of file content."""
    return hashlib.sha256(file_data).hexdigest()[:16]


def get_cache_path(file_hash: str) -> Path:
    """Get cache file path for a given hash."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{file_hash}.json"


def is_cached(file_hash: str, ttl_hours: int = DEFAULT_TTL_HOURS) -> bool:
    """Check if processing result is cached and valid."""
    cache_path = get_cache_path(file_hash)
    
    if not cache_path.exists():
        return False
    
    # Check TTL
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            cached_time = datetime.fromisoformat(data.get('cached_at', ''))
            
            if datetime.now() - cached_time > timedelta(hours=ttl_hours):
                # Cache expired
                cache_path.unlink()
                return False
            
            return True
    except Exception:
        return False


def get_cached_result(file_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieve cached processing result."""
    cache_path = get_cache_path(file_hash)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.info(f"Cache hit: {file_hash}")
            return data.get('result')
    except Exception as e:
        logger.error(f"Failed to read cache: {e}")
        return None


def cache_result(
    file_hash: str, 
    result: Dict[str, Any],
    filename: str = ""
) -> None:
    """
    Save processing result to cache.
    
    Args:
        file_hash: Hash of the processed file
        result: Processing result to cache
        filename: Original filename for reference
    """
    cache_path = get_cache_path(file_hash)
    
    # Prepare cacheable data (convert datetime objects to strings)
    cacheable_result = _make_json_serializable(result)
    
    cache_data = {
        'cached_at': datetime.now().isoformat(),
        'filename': filename,
        'hash': file_hash,
        'result': cacheable_result
    }
    
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Cached result: {file_hash}")
    except Exception as e:
        logger.error(f"Failed to cache result: {e}")


def _make_json_serializable(obj: Any) -> Any:
    """Convert non-JSON-serializable objects."""
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_serializable(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, '__dict__'):
        return _make_json_serializable(obj.__dict__)
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)


def clear_cache() -> int:
    """Clear all cached results. Returns number of files deleted."""
    if not CACHE_DIR.exists():
        return 0
    
    count = 0
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            cache_file.unlink()
            count += 1
        except Exception:
            pass
    
    logger.info(f"Cleared {count} cached files")
    return count


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    if not CACHE_DIR.exists():
        return {'count': 0, 'size_mb': 0}
    
    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    
    return {
        'count': len(files),
        'size_mb': round(total_size / (1024 * 1024), 2)
    }


# Streamlit-integrated caching decorator
def cached_process(ttl_hours: int = DEFAULT_TTL_HOURS):
    """
    Decorator for caching processing functions.
    
    Usage:
        @cached_process(ttl_hours=24)
        def process_pdf(file_hash: str, file_data: bytes) -> Dict:
            ...
    """
    def decorator(func):
        def wrapper(file_hash: str, *args, **kwargs):
            # Check cache first
            cached = get_cached_result(file_hash)
            if cached is not None:
                return cached
            
            # Process and cache
            result = func(file_hash, *args, **kwargs)
            cache_result(file_hash, result)
            return result
        
        return wrapper
    return decorator
