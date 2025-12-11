"""
Structured Logging Configuration

Sets up JSON-formatted logging for production observability.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging.

    Outputs logs in JSON format for easy parsing by log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        # Base log data
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "metadata"):
            log_data["metadata"] = record.metadata

        # Add file location info for errors
        if record.levelno >= logging.ERROR:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", use_json: bool = True) -> None:
    """
    Configure application logging.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting (default True for production)
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers.clear()

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Set formatter
    if use_json:
        formatter = JSONFormatter()
    else:
        # Simple format for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    console_handler.setFormatter(formatter)

    # Add handler
    root_logger.addHandler(console_handler)

    # Log initial message
    root_logger.info(
        "Logging configured",
        extra={
            "metadata": {
                "log_level": log_level,
                "json_format": use_json,
            }
        },
    )


def log_event(
    logger: logging.Logger, level: str, event: str, metadata: Dict[str, Any] = None
) -> None:
    """
    Log a structured event with metadata.

    Args:
        logger: Logger instance to use
        level: Log level (info, warning, error, etc.)
        event: Event description
        metadata: Additional structured data
    """
    log_func = getattr(logger, level.lower())

    if metadata:
        log_func(event, extra={"metadata": metadata})
    else:
        log_func(event)


# Convenience logger for application
app_logger = logging.getLogger("subtitle_service")
