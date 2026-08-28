"""Tests for database backend persistence semantics."""
from __future__ import annotations

from unittest.mock import patch


def test_json_save_all_users_does_not_delete_users_missing_from_snapshot(tmp_path):
    from utils.db import JSONBackend

    db = JSONBackend()
    with patch("utils.storage.get_data_dir", return_value=tmp_path):
        db.save_all_users({
            "alice": {"username": "alice", "tier": "free"},
            "bob": {"username": "bob", "tier": "pro"},
        })
        db.save_user_data("bob", "history.json", [{"id": "keep-bob"}])
        db.save_all_users({"alice": {"username": "alice", "tier": "team"}})

        users = db.get_all_users()
        assert users["alice"]["tier"] == "team"
        assert users["bob"]["tier"] == "pro"
        assert (tmp_path / "users" / "bob").exists()
        assert db.load_user_data("bob", "history.json", default=[]) == [{"id": "keep-bob"}]


def test_json_save_all_users_empty_snapshot_is_noop(tmp_path):
    from utils.db import JSONBackend

    db = JSONBackend()
    with patch("utils.storage.get_data_dir", return_value=tmp_path):
        db.save_all_users({"alice": {"username": "alice"}})
        db.save_user_data("alice", "history.json", [{"id": "keep"}])
        db.save_all_users({})

        assert db.get_all_users() == {"alice": {"username": "alice"}}
        assert (tmp_path / "users" / "alice").exists()
        assert db.load_user_data("alice", "history.json", default=[]) == [{"id": "keep"}]


def test_json_upsert_user_does_not_rewrite_other_users(tmp_path):
    from utils.db import JSONBackend

    db = JSONBackend()
    with patch("utils.storage.get_data_dir", return_value=tmp_path):
        db.upsert_user("alice", {"username": "alice", "tier": "free"})
        db.upsert_user("bob", {"username": "bob", "tier": "pro"})
        db.upsert_user("alice", {"username": "alice", "tier": "enterprise"})
        users = db.get_all_users()
        assert users["alice"]["tier"] == "enterprise"
        assert users["bob"]["tier"] == "pro"


def test_sqlite_save_all_users_does_not_delete_users_missing_from_snapshot(tmp_path):
    from utils.db import SQLiteBackend

    db = SQLiteBackend(tmp_path / "app.sqlite3")
    db.save_all_users({
        "alice": {"username": "alice", "tier": "free"},
        "bob": {"username": "bob", "tier": "pro"},
    })
    db.save_user_data("bob", "history.json", [{"id": "keep-bob"}])
    db.save_all_users({"alice": {"username": "alice", "tier": "team"}})

    assert db.get_user("bob")["tier"] == "pro"
    assert db.load_user_data("bob", "history.json", default=[]) == [{"id": "keep-bob"}]


def test_sqlite_save_all_users_empty_snapshot_is_noop(tmp_path):
    from utils.db import SQLiteBackend

    db = SQLiteBackend(tmp_path / "app.sqlite3")
    db.save_all_users({"alice": {"username": "alice"}})
    db.save_user_data("alice", "history.json", [{"id": "keep"}])
    db.save_all_users({})

    assert db.get_all_users() == {"alice": {"username": "alice"}}
    assert db.load_user_data("alice", "history.json", default=[]) == [{"id": "keep"}]


def test_sqlite_upsert_user_updates_one_row(tmp_path):
    from utils.db import SQLiteBackend

    db = SQLiteBackend(tmp_path / "app.sqlite3")
    db.upsert_user("alice", {"username": "alice", "tier": "free"})
    db.upsert_user("bob", {"username": "bob", "tier": "pro"})
    db.upsert_user("alice", {"username": "alice", "tier": "enterprise"})
    assert db.get_user("alice")["tier"] == "enterprise"
    assert db.get_user("bob")["tier"] == "pro"


def test_postgres_save_all_users_does_not_issue_not_in_delete():
    from utils.db import PostgreSQLBackend

    class FakeCursor:
        def __init__(self):
            self.calls = []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, query, params=None):
            self.calls.append((" ".join(query.split()), params))

    class FakeConnection:
        def __init__(self):
            self.cursor_obj = FakeCursor()
            self.committed = False
            self.closed = False

        def cursor(self):
            return self.cursor_obj

        def commit(self):
            self.committed = True

        def close(self):
            self.closed = True

    connection = FakeConnection()
    db = object.__new__(PostgreSQLBackend)
    db._get_conn = lambda: connection
    db.save_all_users({"alice": {"username": "alice"}})

    sql = " ".join(call[0] for call in connection.cursor_obj.calls)
    assert "DELETE FROM user_data" not in sql
    assert "DELETE FROM users_db" not in sql
    assert "INSERT INTO users_db" in sql
    assert connection.committed is True
    assert connection.closed is True
