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
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def save_json(filename: str, data) -> None:
    """
    Atomic write to data/{filename}.

    Writes to a .tmp file first, then uses os.replace for atomicity.
    """
    filepath = get_data_dir() / filename
    tmp_path = filepath.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, filepath)
