"""
Logging Utility Module
Provides centralized logging configuration for the Email Assistant application.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(name: str, log_level: str = 'INFO') -> logging.Logger:
    """
    Set up and configure a logger with file and console handlers.

    Args:
        name: Logger name (typically __name__ of the calling module)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )

    # File handler (detailed logs)
    log_file = log_dir / 'email_assistant.log'
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)  # Capture all levels in file
    file_handler.setFormatter(detailed_formatter)

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def log_exception(logger: logging.Logger, exception: Exception, context: str = ''):
    """
    Log an exception with full traceback and optional context.

    Args:
        logger: Logger instance
        exception: The exception to log
        context: Additional context information
    """
    error_msg = f"{context}: {str(exception)}" if context else str(exception)
    logger.error(error_msg, exc_info=True)


def log_performance(logger: logging.Logger, operation: str, duration: float):
    """
    Log performance metrics for an operation.

    Args:
        logger: Logger instance
        operation: Name of the operation
        duration: Duration in seconds
    """
    logger.info(f"Performance - {operation}: {duration:.2f}s")


def log_api_call(logger: logging.Logger, api_name: str, success: bool, cached: bool = False):
    """
    Log API call information.

    Args:
        logger: Logger instance
        api_name: Name of the API (e.g., 'Gmail', 'Gemini')
        success: Whether the call was successful
        cached: Whether the result was served from cache
    """
    status = "SUCCESS" if success else "FAILED"
    cache_info = " (CACHED)" if cached else ""
    logger.info(f"API Call - {api_name}: {status}{cache_info}")


def log_cache_operation(logger: logging.Logger, operation: str, key: str, hit: bool = None):
    """
    Log cache operations.

    Args:
        logger: Logger instance
        operation: Type of operation (GET, SET, EVICT)
        key: Cache key
        hit: For GET operations, whether it was a hit or miss
    """
    if operation == 'GET' and hit is not None:
        result = "HIT" if hit else "MISS"
        logger.debug(f"Cache {operation} - {key}: {result}")
    else:
        logger.debug(f"Cache {operation} - {key}")


def log_email_processing(logger: logging.Logger, email_count: int, category: str = None):
    """
    Log email processing information.

    Args:
        logger: Logger instance
        email_count: Number of emails processed
        category: Optional category name
    """
    if category:
        logger.info(f"Processed {email_count} emails in category: {category}")
    else:
        logger.info(f"Processed {email_count} emails")


# Create a default logger for the application
default_logger = setup_logger('email_assistant')
