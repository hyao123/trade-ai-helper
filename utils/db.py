"""
utils/db.py
-----------
Database abstraction layer supporting multiple backends.
Provides a unified interface that can be switched between:
  - JSON file storage (default, for development / Streamlit Cloud)
  - PostgreSQL (for production / commercial deployment)

Backend is selected by the DATABASE_URL environment variable:
  - Not set or empty: uses JSON file backend
  - postgresql://...: uses PostgreSQL backend

Usage:
    from utils.db import get_db

    db = get_db()
    db.save_user(username, data)
    user = db.get_user(username)
    db.save_customers(username, customers_list)
"""
from __future__ import annotations

import abc
from typing import Any

from utils.logger import get_logger
from utils.secrets import get_secret

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
    This is the default backend for development and Streamlit Cloud.
    """

    def get_all_users(self) -> dict:
        from utils.storage import load_json
        return load_json("users_db.json", default={})

    def save_all_users(self, users: dict) -> None:
        from utils.storage import save_json
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


class PostgreSQLBackend(DatabaseBackend):
    """
    PostgreSQL storage backend using psycopg2.
    Requires DATABASE_URL to be set.

    Data is stored in a key-value style:
      - users table for user accounts
      - user_data table for per-user collections (JSON)
      - global_data table for app-wide collections (JSON)
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
        try:
            conn = self._get_conn()
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
            conn.close()
            logger.info("PostgreSQL tables ensured")
        except Exception as e:
            logger.error("Failed to ensure PostgreSQL tables: %s", e)
            raise

    def get_all_users(self) -> dict:
        import json
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT username, data FROM users_db")
            rows = cur.fetchall()
        conn.close()
        return {row[0]: row[1] for row in rows}

    def save_all_users(self, users: dict) -> None:
        import json
        conn = self._get_conn()
        with conn.cursor() as cur:
            # Upsert all users
            for username, data in users.items():
                cur.execute("""
                    INSERT INTO users_db (username, data, updated_at)
                    VALUES (%s, %s, NOW())
                    ON CONFLICT (username)
                    DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
                """, (username, json.dumps(data)))
        conn.commit()
        conn.close()

    def get_user(self, username: str) -> dict | None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM users_db WHERE username = %s", (username,))
            row = cur.fetchone()
        conn.close()
        return row[0] if row else None

    def load_user_data(self, username: str, collection: str, default: Any = None) -> Any:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT data FROM user_data WHERE username = %s AND collection = %s",
                (username, collection),
            )
            row = cur.fetchone()
        conn.close()
        return row[0] if row else (default if default is not None else [])

    def save_user_data(self, username: str, collection: str, data: Any) -> None:
        import json
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_data (username, collection, data, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (username, collection)
                DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
            """, (username, collection, json.dumps(data)))
        conn.commit()
        conn.close()

    def load_global_data(self, collection: str, default: Any = None) -> Any:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT data FROM global_data WHERE collection = %s", (collection,))
            row = cur.fetchone()
        conn.close()
        return row[0] if row else (default if default is not None else [])

    def save_global_data(self, collection: str, data: Any) -> None:
        import json
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO global_data (collection, data, updated_at)
                VALUES (%s, %s, NOW())
                ON CONFLICT (collection)
                DO UPDATE SET data = EXCLUDED.data, updated_at = NOW()
            """, (collection, json.dumps(data)))
        conn.commit()
        conn.close()


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------
_db_instance: DatabaseBackend | None = None


def get_db() -> DatabaseBackend:
    """
    Get the database backend singleton.

    Returns JSONBackend by default.
    Returns PostgreSQLBackend if DATABASE_URL is configured.
    """
    global _db_instance
    if _db_instance is not None:
        return _db_instance

    database_url = get_secret("DATABASE_URL")
    if database_url and database_url.startswith("postgres"):
        try:
            _db_instance = PostgreSQLBackend(database_url)
            logger.info("Using PostgreSQL backend")
        except Exception as e:
            logger.warning("PostgreSQL init failed, falling back to JSON: %s", e)
            _db_instance = JSONBackend()
    else:
        _db_instance = JSONBackend()
        logger.info("Using JSON file backend")

    return _db_instance
