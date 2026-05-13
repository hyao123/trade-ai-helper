"""
utils/logger.py
---------------
Application logging configuration.
Configures file + console handlers with configurable log level.
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> logging.Logger:
    """
    Configure application-wide logging.

    - Reads LOG_LEVEL from environment (default: INFO)
    - Console handler: INFO+ level
    - File handler: DEBUG+ level, logs/app.log, 5MB rotation, 3 backups
    - Returns the root application logger
    """
    # Determine log level from environment
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    if level_name not in valid_levels:
        print(f"[logger] Invalid LOG_LEVEL '{level_name}', falling back to INFO")
        level_name = "INFO"

    level = getattr(logging, level_name)

    # Create logs directory
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "app.log"

    # Configure root logger for the app
    logger = logging.getLogger("trade_ai")
    logger.setLevel(logging.DEBUG)  # Capture all, let handlers filter

    # Avoid adding duplicate handlers on reload
    if logger.handlers:
        return logger

    # Format
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Console handler (INFO+)
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    logger.addHandler(console)

    # File handler (DEBUG+, rotating)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.info("Logging configured: level=%s, file=%s", level_name, log_file)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger under the trade_ai namespace."""
    return logging.getLogger(f"trade_ai.{name}")
