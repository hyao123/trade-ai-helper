"""
utils/db.py
-----------
Database abstraction layer supporting multiple backends.
Provides a unified interface that can be switched between:
  - JSON file storage (default, for local development)
  - SQLite (simple persistent demo/single-instance deployment)
  - PostgreSQL (production / commercial deployment)

Backend is selected by configuration:
  - DATABASE_URL=postgres...: uses PostgreSQL backend
  - DATABASE_URL=sqlite:///path/to/app.sqlite3: uses SQLite backend
  - SQLITE_DB_PATH=/path/to/app.sqlite3: uses SQLite backend
  - Not set or empty: uses JSON file backend

Usage:
    from utils.db import get_db

    db = get_db()
    db.save_all_users(users)
    user = db.get_user(username)
    db.save_user_data(username, "history.json", history)
"""
from __future__ import annotations

import abc
import json
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from utils.logger import get_logger
from utils.secrets import get_secret
from utils.storage import get_data_dir

logger = get_logger("db")


class DatabaseBackend(abc.ABC):
    """Abstract interface for data persistence backends."""

    # ── Users ─────────────────────────────────────────
    @abc.abstractmethod
    def get_all_users(self) -> dict:
        """Return the complete users database as a dict."""
        ...

    @abc.abstractmethod
    def save_all_users(self, users: dict) -> None:
        """Persist the complete users database."""
        ...

    @abc.abstractmethod
    def get_user(self, username: str) -> dict | None:
        """Get a single user by username."""
        ...

    # ── Per-user data ─────────────────────────────────
    @abc.abstractmethod
    def load_user_data(self, username: str, collection: str, default: Any = None) -> Any:
        """Load a data collection for a specific user."""
        ...

    @abc.abstractmethod
    def save_user_data(self, username: str, collection: str, data: Any) -> None:
        """Save a data collection for a specific user."""
        ...

    # ── Global data ───────────────────────────────────
    @abc.abstractmethod
    def load_global_data(self, collection: str, default: Any = None) -> Any:
        """Load a global (non-user-specific) data collection."""
        ...

    @abc.abstractmethod
    def save_global_data(self, collection: str, data: Any) -> None:
        """Save a global data collection."""
        ...


class JSONBackend(DatabaseBackend):
    """
    JSON file-based storage backend.
    Delegates to the existing utils/storage.py functions.
    This is the default backend for development.
    """

    def get_all_users(self) -> dict:
        from utils.storage import load_json
        return load_json("users_db.json", default={})

    def save_all_users(self, users: dict) -> None:
        from utils.storage import get_data_dir, save_json
        users_dir = get_data_dir() / "users"
        if users_dir.exists():
            valid_usernames = set(users)
            for child in users_dir.iterdir():
                if child.is_dir() and child.name not in valid_usernames:
                    shutil.rmtree(child)
        save_json("users_db.json", users)

    def get_user(self, username: str) -> dict | None:
        users = self.get_all_users()
        return users.get(username)

    def load_user_data(self, username: str, collection: str, default: Any = None) -> Any:
        from utils.storage import load_user_json
        return load_user_json(username, collection, default=default if default is not None else [])

    def save_user_data(self, username: str, collection: str, data: Any) -> None:
        from utils.storage import save_user_json
        save_user_json(username, collection, data)

    def load_global_data(self, collection: str, default: Any = None) -> Any:
        from utils.storage import load_json
        return load_json(collection, default=default if default is not None else [])

    def save_global_data(self, collection: str, data: Any) -> None:
        from utils.storage import save_json
        save_json(collection, data)


def _json_loads(value: str | bytes | None, default: Any = None) -> Any:
    if value is None:
        return default if default is not None else []
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default if default is not None else []


def _json_dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


class SQLiteBackend(DatabaseBackend):
    """
    SQLite storage backend for single-instance demos and lightweight deployments.

    Data uses the same logical shape as PostgreSQLBackend:
      - users_db(username, data)
      - user_data(username, collection, data)
      - global_data(collection, data)

    Reuses thread-local SQLite connections to eliminate per-query connection
    and PRAGMA initialization overhead.
    """

    def __init__(self, db_path: str | Path):
        self._path = Path(db_path).expanduser()
        if not self._path.is_absolute():
            self._path = get_data_dir() / self._path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create a thread-local SQLite connection with WAL mode and foreign keys."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._path, timeout=30, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return conn

    def close(self) -> None:
        """Close the active thread-local connection if open."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
            self._local.conn = None

    def _ensure_tables(self) -> None:
        with self._get_conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users_db (
                    username TEXT PRIMARY KEY,
                    data TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS user_data (
                    username TEXT NOT NULL,
                    collection TEXT NOT NULL,
                    data TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (username, collection)
                );
                CREATE TABLE IF NOT EXISTS global_data (
                    collection TEXT PRIMARY KEY,
                    data TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
        logger.info("SQLite tables ensured at %s", self._path)

    def get_all_users(self) -> dict:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT username, data FROM users_db").fetchall()
        return {row["username"]: _json_loads(row["data"], default={}) for row in rows}

    def save_all_users(self, users: dict) -> None:
        with self._get_conn() as conn:
            usernames = list(users)
            if usernames:
                placeholders = ",".join("?" for _ in usernames)
                conn.execute(f"DELETE FROM user_data WHERE username NOT IN ({placeholders})", usernames)
                conn.execute(f"DELETE FROM users_db WHERE username NOT IN ({placeholders})", usernames)
            else:
                conn.execute("DELETE FROM user_data")
                conn.execute("DELETE FROM users_db")

            for username, data in users.items():
                conn.execute(
                    """
                    INSERT INTO users_db (username, data, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(username)
                    DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP
                    """,
                    (username, _json_dumps(data)),
                )

    def get_user(self, username: str) -> dict | None:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data FROM users_db WHERE username = ?",
                (username,),
            ).fetchone()
        return _json_loads(row["data"], default={}) if row else None

    def load_user_data(self, username: str, collection: str, default: Any = None) -> Any:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data FROM user_data WHERE username = ? AND collection = ?",
                (username, collection),
            ).fetchone()
        return _json_loads(row["data"], default=default) if row else (default if default is not None else [])

    def save_user_data(self, username: str, collection: str, data: Any) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO user_data (username, collection, data, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(username, collection)
                DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP
                """,
                (username, collection, _json_dumps(data)),
            )

    def load_global_data(self, collection: str, default: Any = None) -> Any:
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT data FROM global_data WHERE collection = ?",
                (collection,),
            ).fetchone()
        return _json_loads(row["data"], default=default) if row else (default if default is not None else [])

    def save_global_data(self, collection: str, data: Any) -> None:
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO global_data (collection, data, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(collection)
                DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP
                """,
                (collection, _json_dumps(data)),
            )


class PostgreSQLBackend(DatabaseBackend):
    """
    PostgreSQL storage backend using psycopg2.
    Requires DATABASE_URL to be set.

    Data is stored in a key-value style:
      - users table for user accounts
      - user_data table for per-user collections (JSON)
      - global_data table for app-wide collections (JSON)

    All methods use try/finally to guarantee connection cleanup even on
    exceptions, preventing connection leaks in production.
    """

    def __init__(self, database_url: str):
        self._url = database_url
        self._ensure_tables()

    def _get_conn(self):
        """Get a database connection."""
        import psycopg2
        return psycopg2.connect(self._url)

    def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users_db (
                        username TEXT PRIMARY KEY,
                        data JSONB NOT NULL DEFAULT '{}',
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                    CREATE TABLE IF NOT EXISTS user_data (
                        username TEXT NOT NULL,
                        collection TEXT NOT NULL,
                        data JSONB NOT NULL DEFAULT '[]',
                        updated_at TIMESTAMPTZ DEFAULT NOW(),
                        PRIMARY KEY (username, collection)
                    );
                    CREATE TABLE IF NOT EXISTS global_data (
                        collection TEXT PRIMARY KEY,
                        data JSONB NOT NULL DEFAULT '[]',
                        updated_at TIMESTAMPTZ DEFAULT NOW()
                    );
                """)
            conn.commit()
            logger.info("PostgreSQL tables ensured")
        except Exception as e:
            logger.error("Failed to ensure PostgreSQL tables: %s", e)
            raise
        finally:
            conn.close()

    def get_all_users(self) -> dict:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT username, data FROM users_db")
                rows = cur.fetchall()
            return {row[0]: row[1] for row in rows}
        finally:
            conn.close()

    def save_all_users(self, users: dict) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                usernames = list(users)
                if usernames:
                    placeholders = ", ".join(["%s"] * len(usernames))
                    cur.execute(
                        f"DELETE FROM user_data WHERE username NOT IN ({placeholders})",
                        tuple(usernames),
                    )
                    cur.execute(
                        f"DELETE FROM users_db WHERE username NOT IN ({placeholders})",
                        tuple(usernames),
                    )
                else:
                    cur.execute("DELETE FROM user_data")
                    cur.execute("DELETE FROM users_db")

                for username, data in users.items():
                    cur.execute("""
                        INSERT INTO users_db (username, data, updated_at)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (username)
                        DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                    """, (username, json.dumps(data)))
            conn.commit()
        finally:
            conn.close()

    def get_user(self, username: str) -> dict | None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM users_db WHERE username = %s", (username,))
                row = cur.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def load_user_data(self, username: str, collection: str, default: Any = None) -> Any:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data FROM user_data WHERE username = %s AND collection = %s",
                    (username, collection),
                )
                row = cur.fetchone()
            return row[0] if row else (default if default is not None else [])
        finally:
            conn.close()

    def save_user_data(self, username: str, collection: str, data: Any) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO user_data (username, collection, data, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (username, collection)
                    DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                """, (username, collection, json.dumps(data)))
            conn.commit()
        finally:
            conn.close()

    def load_global_data(self, collection: str, default: Any = None) -> Any:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT data FROM global_data WHERE collection = %s", (collection,))
                row = cur.fetchone()
            return row[0] if row else (default if default is not None else [])
        finally:
            conn.close()

    def save_global_data(self, collection: str, data: Any) -> None:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO global_data (collection, data, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (collection)
                    DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                """, (collection, json.dumps(data)))
            conn.commit()
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------
_db_instance: DatabaseBackend | None = None
_db_signature: tuple[str, str, str] | None = None


def _sqlite_path_from_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    if parsed.scheme != "sqlite":
        raise ValueError("Not a sqlite URL")
    if parsed.netloc and parsed.netloc not in ("", "localhost"):
        # sqlite:///relative.db or sqlite:////absolute.db are supported.
        # Remote sqlite hosts are not meaningful here.
        raise ValueError("SQLite DATABASE_URL must not include a remote host")
    path = unquote(parsed.path or "")
    if path.startswith("/") and not database_url.startswith("sqlite:////"):
        path = path.lstrip("/")
    return path or "trade_ai_helper.sqlite3"


def get_db() -> DatabaseBackend:
    """
    Get the database backend singleton.

    Returns JSONBackend by default.
    Returns SQLiteBackend if SQLITE_DB_PATH or sqlite DATABASE_URL is configured.
    Returns PostgreSQLBackend if DATABASE_URL starts with postgres.
    """
    global _db_instance, _db_signature
    database_url = get_secret("DATABASE_URL")
    sqlite_path = get_secret("SQLITE_DB_PATH")
    signature = (database_url or "", sqlite_path or "", str(get_data_dir().resolve()))
    if _db_instance is not None and _db_signature == signature:
        return _db_instance

    if database_url and database_url.startswith("postgres"):
        try:
            _db_instance = PostgreSQLBackend(database_url)
            logger.info("Using PostgreSQL backend")
        except Exception as e:
            logger.warning("PostgreSQL init failed, falling back to JSON: %s", e)
            _db_instance = JSONBackend()
    elif database_url and database_url.startswith("sqlite:"):
        try:
            _db_instance = SQLiteBackend(_sqlite_path_from_database_url(database_url))
            logger.info("Using SQLite backend from DATABASE_URL")
        except Exception as e:
            logger.warning("SQLite init failed, falling back to JSON: %s", e)
            _db_instance = JSONBackend()
    elif sqlite_path:
        try:
            _db_instance = SQLiteBackend(sqlite_path)
            logger.info("Using SQLite backend from SQLITE_DB_PATH")
        except Exception as e:
            logger.warning("SQLite init failed, falling back to JSON: %s", e)
            _db_instance = JSONBackend()
    else:
        _db_instance = JSONBackend()
        logger.info("Using JSON file backend")

    _db_signature = signature
    return _db_instance
