"""
utils/storage.py
----------------
JSON file-based persistence layer.
Reads/writes JSON files in a data/ directory for cross-session data persistence.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from utils.logger import get_logger

logger = get_logger("storage")


def get_data_dir() -> Path:
    """Return the data/ directory relative to project root. Creates it if needed."""
    data_dir = Path(__file__).resolve().parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def load_json(filename: str, default=None):
    """
    Load JSON from data/{filename}.

    Returns default (or [] if default is None) if file not found or invalid.
    """
    if default is None:
        default = []
    filepath = get_data_dir() / filename
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Loaded %s", filename)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        logger.debug("File not found or invalid: %s, using default", filename)
        return default


def save_json(filename: str, data) -> None:
    """
    Atomic write to data/{filename}.

    Writes to a .tmp file first, then uses os.replace for atomicity.
    """
    filepath = get_data_dir() / filename
    tmp_path = filepath.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
        logger.debug("Saved %s", filename)
    except OSError as e:
        logger.error("Failed to save %s: %s", filename, e)
        raise


def get_user_data_dir(username: str) -> Path:
    """Return data/users/{username}/ directory. Creates it if needed."""
    if not username.isalnum():
        raise ValueError("Invalid username")
    user_dir = get_data_dir() / "users" / username
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir


def load_user_json(username: str, filename: str, default=None):
    """
    Load JSON from data/users/{username}/{filename}.

    Returns default (or [] if default is None) if file not found or invalid.
    """
    if default is None:
        default = []
    filepath = get_user_data_dir(username) / filename
    try:
        with open(filepath, encoding="utf-8") as f:
            data = json.load(f)
        logger.debug("Loaded user file %s/%s", username, filename)
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        logger.debug("User file not found or invalid: %s/%s, using default", username, filename)
        return default


def save_user_json(username: str, filename: str, data) -> None:
    """
    Atomic write to data/users/{username}/{filename}.

    Writes to a .tmp file first, then uses os.replace for atomicity.
    """
    filepath = get_user_data_dir(username) / filename
    tmp_path = filepath.with_suffix(".tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
        logger.debug("Saved user file %s/%s", username, filename)
    except OSError as e:
        logger.error("Failed to save user file %s/%s: %s", username, filename, e)
        raise
