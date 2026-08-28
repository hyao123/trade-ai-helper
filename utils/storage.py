"""
utils/storage.py
----------------
JSON file-based persistence layer.
Reads/writes JSON files in a data/ directory for cross-session data persistence.
"""

from __future__ import annotations

import contextlib
import copy
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from utils.logger import get_logger

logger = get_logger("storage")


@contextlib.contextmanager
def _file_lock(filepath: Path):
    """Serialize JSON file access with a best-effort cross-platform lock file.

    The lock is intentionally best-effort: if the underlying OS lock cannot be
    acquired (e.g. ``msvcrt.locking`` raising ``OSError``/``PermissionError`` on
    restricted filesystems or sandboxed environments), we fall back to an
    unlocked context rather than failing the read/write entirely. This mirrors
    the documented intent in ``storage.py``'s module docstring and keeps data
    persistence working even when advisory locking is unavailable.
    """
    lock_path = filepath.with_name(f"{filepath.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        lock_file = open(lock_path, "a+")
    except OSError as exc:
        logger.debug("Lock file unavailable (%s), using unlocked fallback: %s", lock_path, exc)
        yield
        return

    with lock_file:
        if os.name == "nt":
            with _windows_lock(lock_file, lock_path):
                yield
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def _windows_lock(lock_file, lock_path: Path):
    """Windows-specific advisory lock around ``lock_file``'s first byte.

    Uses non-blocking ``LK_NBLCK`` with bounded retries so we never hang a
    request on a lock held by a crashed/leaked process. On any ``OSError``
    (including ``PermissionError`` in restricted/sandboxed filesystems) we
    degrade to an unlocked context rather than abort persistence.
    """
    import msvcrt

    # Ensure the file has at least one byte so the byte-range lock is valid.
    try:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(" ")
            lock_file.flush()
    except OSError:
        yield
        return

    lock_file.seek(0)

    acquired = False
    delay = 0.05
    for _ in range(10):
        try:
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            acquired = True
            break
        except OSError:
            time.sleep(delay)
            delay = min(delay * 1.5, 0.5)

    if not acquired:
        logger.debug("Could not acquire OS lock for %s; using unlocked fallback", lock_path)
        yield
        return

    try:
        yield
    finally:
        try:
            lock_file.seek(0)
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            # Unlock may fail if the handle was closed or lock released externally.
            pass


def _quarantine_invalid_json(filepath: Path) -> None:
    """Preserve an invalid JSON file copy for later inspection."""
    if not filepath.exists():
        return
    timestamp = int(time.time() * 1000)
    corrupt_path = filepath.with_name(f"{filepath.name}.corrupt.{timestamp}")
    try:
        shutil.copy2(filepath, corrupt_path)
        logger.warning("Invalid JSON quarantined: %s -> %s", filepath, corrupt_path)
    except OSError as exc:
        logger.warning("Failed to quarantine invalid JSON %s: %s", filepath, exc)


def _load_json_file(filepath: Path, default):
    """Load JSON from a concrete path under a file lock."""
    try:
        with _file_lock(filepath):
            with open(filepath, encoding="utf-8") as f:
                return json.load(f)
    except FileNotFoundError:
        logger.debug("File not found: %s, using default", filepath)
        return default
    except json.JSONDecodeError:
        logger.warning("Invalid JSON: %s, using default", filepath)
        _quarantine_invalid_json(filepath)
        return default
    except OSError as exc:
        logger.debug("Unable to load %s: %s, using default", filepath, exc)
        return default


def _save_json_file(filepath: Path, data) -> None:
    """Atomically write JSON to a concrete path with lock and backup."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    with _file_lock(filepath):
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=filepath.parent,
                prefix=f".{filepath.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                json.dump(data, tmp_file, ensure_ascii=False, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                tmp_path = Path(tmp_file.name)

            if filepath.exists():
                backup_path = filepath.with_name(f"{filepath.name}.bak")
                shutil.copy2(filepath, backup_path)

            os.replace(tmp_path, filepath)
            tmp_path = None
            logger.debug("Saved %s", filepath)
        except OSError as e:
            logger.error("Failed to save %s: %s", filepath, e)
            raise
        finally:
            if tmp_path and tmp_path.exists():
                with contextlib.suppress(OSError):
                    tmp_path.unlink()


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
    return _load_json_file(get_data_dir() / filename, default)


def save_json(filename: str, data) -> None:
    """
    Atomic write to data/{filename}.

    Writes through a lock-protected temporary file, preserving a .bak copy
    of the previous valid file before replacing it.
    """
    _save_json_file(get_data_dir() / filename, data)


def mutate_json(filename: str, mutator, default=None):
    """Atomically read, mutate, and write one JSON document.

    The lock covers the complete read-modify-write transaction, preventing
    concurrent callers from overwriting each other's updates. ``mutator``
    receives the decoded value and must return the value to persist.
    """
    if default is None:
        default = []
    filepath = get_data_dir() / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    with _file_lock(filepath):
        try:
            try:
                with open(filepath, encoding="utf-8") as source:
                    current = json.load(source)
            except FileNotFoundError:
                current = copy.deepcopy(default)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON: %s, using default", filepath)
                _quarantine_invalid_json(filepath)
                current = copy.deepcopy(default)

            updated = mutator(current)
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=filepath.parent,
                prefix=f".{filepath.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                json.dump(updated, tmp_file, ensure_ascii=False, indent=2)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                tmp_path = Path(tmp_file.name)

            if filepath.exists():
                shutil.copy2(filepath, filepath.with_name(f"{filepath.name}.bak"))
            os.replace(tmp_path, filepath)
            tmp_path = None
            return updated
        finally:
            if tmp_path and tmp_path.exists():
                with contextlib.suppress(OSError):
                    tmp_path.unlink()


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
    return _load_json_file(get_user_data_dir(username) / filename, default)


def save_user_json(username: str, filename: str, data) -> None:
    """
    Atomic write to data/users/{username}/{filename}.

    Writes through a lock-protected temporary file, preserving a .bak copy
    of the previous valid file before replacing it.
    """
    _save_json_file(get_user_data_dir(username) / filename, data)


# ---------------------------------------------------------------------------
# Streamlit session-state backed JSON helpers
# ---------------------------------------------------------------------------
def get_storage_scope() -> str:
    """Return a stable cache scope for the active storage backend."""
    return str(get_data_dir().resolve())


def _copy_default(default: Any) -> Any:
    """Return an isolated default value for mutable JSON defaults."""
    return copy.deepcopy(default() if callable(default) else default)


def _scoped_key(base_key: str, username: str | None = None) -> str:
    """Return a shared or per-user session-state key."""
    return f"{base_key}_{username}" if username else base_key


def load_scoped_session_json(
    session_state,
    filename: str,
    state_key: str,
    loaded_key: str,
    scope_key: str,
    default: Any,
    username: str | None = None,
):
    """Load JSON into session_state and invalidate cache when storage scope changes."""
    resolved_state_key = _scoped_key(state_key, username)
    resolved_loaded_key = _scoped_key(loaded_key, username)
    resolved_scope_key = _scoped_key(scope_key, username)
    scope = get_storage_scope()

    if (
        resolved_state_key in session_state
        and session_state.get(resolved_loaded_key)
        and resolved_scope_key not in session_state
    ):
        # Backfill scope metadata for legacy/tests that populated the cache
        # before scope-aware keys existed.
        session_state[resolved_scope_key] = scope

    if (
        resolved_state_key not in session_state
        or not session_state.get(resolved_loaded_key)
        or session_state.get(resolved_scope_key) != scope
    ):
        fallback = _copy_default(default)
        if username:
            session_state[resolved_state_key] = load_user_json(username, filename, default=fallback)
        else:
            session_state[resolved_state_key] = load_json(filename, default=fallback)
        session_state[resolved_loaded_key] = True
        session_state[resolved_scope_key] = scope

    return session_state[resolved_state_key]


def save_scoped_session_json(
    session_state,
    filename: str,
    state_key: str,
    default: Any,
    username: str | None = None,
) -> None:
    """Persist a shared or per-user session-state JSON value."""
    resolved_state_key = _scoped_key(state_key, username)
    data = session_state.get(resolved_state_key, _copy_default(default))
    if username:
        save_user_json(username, filename, data)
    else:
        save_json(filename, data)


def import_scoped_session_json(
    session_state,
    filename: str,
    data,
    state_key: str,
    loaded_key: str,
    scope_key: str,
    username: str | None = None,
) -> None:
    """Replace cached JSON data, update scope metadata, and persist it."""
    resolved_state_key = _scoped_key(state_key, username)
    resolved_loaded_key = _scoped_key(loaded_key, username)
    resolved_scope_key = _scoped_key(scope_key, username)

    session_state[resolved_state_key] = data
    session_state[resolved_loaded_key] = True
    session_state[resolved_scope_key] = get_storage_scope()

    if username:
        save_user_json(username, filename, data)
    else:
        save_json(filename, data)
