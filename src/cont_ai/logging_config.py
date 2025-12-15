"""
Logging Configuration Module for Cont.AI

Provides centralized logging configuration with:
- Console output with colored levels
- Optional file logging
- Structured format for debugging
"""
import logging
import sys
from typing import Optional
from pathlib import Path


# Custom formatter with colors for console output
class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to log levels for console output."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    ICONS = {
        'DEBUG': '🔍',
        'INFO': '✅',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'CRITICAL': '🚨',
    }

    def format(self, record: logging.LogRecord) -> str:
        # Add color and icon based on level
        color = self.COLORS.get(record.levelname, '')
        icon = self.ICONS.get(record.levelname, '')
        
        # Store original levelname
        original_levelname = record.levelname
        
        # Modify levelname with color (for console)
        record.levelname = f"{icon} {record.levelname}"
        
        # Format the message
        formatted = super().format(record)
        
        # Restore original levelname
        record.levelname = original_levelname
        
        return f"{color}{formatted}{self.RESET}"


def setup_logger(
    name: str = "cont_ai",
    level: int = logging.INFO,
    log_file: Optional[Path] = None,
    enable_console: bool = True
) -> logging.Logger:
    """
    Configure and return a logger instance.
    
    Args:
        name: Logger name (usually module name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        enable_console: Whether to output to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Console Handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_format = ColoredFormatter(
            fmt='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)
    
    # File Handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_format = logging.Formatter(
            fmt='%(asctime)s | %(name)s | %(levelname)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger with the specified name.
    
    Args:
        name: Module or component name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(f"cont_ai.{name}")


# Default logger instance
logger = setup_logger()
