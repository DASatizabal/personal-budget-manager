"""Logging configuration for the Budget App"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler


# Log directory (same as database location)
LOG_DIR = Path(__file__).parent.parent.parent
LOG_FILE = LOG_DIR / 'budget_app.log'
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3  # Keep 3 backup log files


def setup_logging(level: str = 'INFO', console_output: bool = False) -> logging.Logger:
    """
    Set up application logging.

    Args:
        level: Log level ('DEBUG', 'INFO', 'WARNING', 'ERROR')
        console_output: If True, also output to console

    Returns:
        The configured logger
    """
    # Create logger
    logger = logging.getLogger('budget_app')
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # File handler with rotation
    try:
        file_handler = RotatingFileHandler(
            LOG_FILE,
            maxBytes=MAX_LOG_SIZE,
            backupCount=BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        # If file logging fails, just print a warning
        print(f"Warning: Could not set up file logging: {e}")

    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Optional name suffix for the logger (e.g., 'database', 'import')

    Returns:
        A logger instance
    """
    base_logger = logging.getLogger('budget_app')

    # If no handlers are set up, initialize with defaults
    if not base_logger.handlers:
        setup_logging()

    if name:
        return base_logger.getChild(name)
    return base_logger


# Convenience functions for logging
def log_info(message: str, logger_name: str = None):
    """Log an info message"""
    get_logger(logger_name).info(message)


def log_warning(message: str, logger_name: str = None):
    """Log a warning message"""
    get_logger(logger_name).warning(message)


def log_error(message: str, logger_name: str = None, exc_info: bool = False):
    """Log an error message"""
    get_logger(logger_name).error(message, exc_info=exc_info)


def log_debug(message: str, logger_name: str = None):
    """Log a debug message"""
    get_logger(logger_name).debug(message)


def log_operation(operation: str, details: str = None, logger_name: str = None):
    """Log an operation with optional details"""
    logger = get_logger(logger_name)
    if details:
        logger.info(f"{operation}: {details}")
    else:
        logger.info(operation)


def log_exception(message: str, logger_name: str = None):
    """Log an exception with traceback"""
    get_logger(logger_name).exception(message)
