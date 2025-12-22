import logging
import json
import os
import uuid
import datetime
import traceback
from typing import Any, Dict, Optional
from threading import local

# Thread-local storage for context (like request_id)
_context = local()

class JSONFormatter(logging.Formatter):
    """
    Custom formatter that outputs JSON records.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "request_id": getattr(_context, "request_id", "GLOBAL"),
        }
        
        # Add extra fields if they exist
        if hasattr(record, "extra_fields") and isinstance(record.extra_fields, dict):
            log_data.update(record.extra_fields)
            
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            log_data["stack_trace"] = traceback.format_exc()

        return json.dumps(log_data, ensure_ascii=False)

def setup_logging(log_level: int = logging.INFO, log_file: Optional[str] = "logs/app.log"):
    """
    Configure global logging settings.
    """
    # Create logs directory if it doesn't exist
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    if root_logger.handlers:
        root_logger.handlers.clear()

    # Console Handler (Human-readable during dev, but still structured if needed)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)

    # File Handler (JSON)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(JSONFormatter())
        root_logger.addHandler(file_handler)

    logging.info("Logging infrastructure initialized.", extra={"extra_fields": {"status": "ready"}})

def set_request_id(request_id: str):
    """Set the current request ID in context."""
    _context.request_id = request_id

def get_request_id() -> str:
    """Get the current request ID from context."""
    return getattr(_context, "request_id", str(uuid.uuid4()))

class AILoggerAdapter(logging.LoggerAdapter):
    """
    Adapter that allows passing extra context easily.
    """
    def process(self, msg: Any, kwargs: Any) -> tuple[Any, Any]:
        extra = kwargs.get("extra", {})
        if "extra_fields" not in extra:
            extra["extra_fields"] = {}
        
        # Merge keyword args into extra_fields if they aren't part of Logger.log
        standard_args = {'exc_info', 'stack_info', 'stacklevel', 'extra'}
        new_kwargs = {}
        for key, value in kwargs.items():
            if key in standard_args:
                new_kwargs[key] = value
            else:
                extra["extra_fields"][key] = value
        
        new_kwargs["extra"] = extra
        return msg, new_kwargs

def get_logger(name: str) -> AILoggerAdapter:
    """
    Return a structured logger for the given name.
    """
    return AILoggerAdapter(logging.getLogger(name), {})
