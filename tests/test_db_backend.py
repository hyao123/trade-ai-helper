"""Tests for database backend persistence semantics."""
from __future__ import annotations

from unittest.mock import patch


def test_json_save_all_users_replaces_previous_user_snapshot_and_user_dirs(tmp_path):
    from utils.db import JSONBackend

    db = JSONBackend()
    with patch("utils.storage.get_data_dir", return_value=tmp_path):
        db.save_all_users({
            "alice": {"username": "alice", "tier": "free"},
            "bob": {"username": "bob", "tier": "pro"},
        })
        db.save_user_data("alice", "history.json", [{"id": "keep"}])
        db.save_user_data("bob", "history.json", [{"id": "remove"}])
        db.save_all_users({"alice": {"username": "alice", "tier": "team"}})

        assert db.get_all_users() == {"alice": {"username": "alice", "tier": "team"}}
        assert db.get_user("bob") is None
        assert db.load_user_data("alice", "history.json", default=[]) == [{"id": "keep"}]
        assert (tmp_path / "users" / "alice").exists()
        assert not (tmp_path / "users" / "bob").exists()
        assert db.load_user_data("bob", "history.json", default=[]) == []


def test_json_save_all_users_empty_snapshot_deletes_all_user_dirs(tmp_path):
    from utils.db import JSONBackend

    db = JSONBackend()
    with patch("utils.storage.get_data_dir", return_value=tmp_path):
        db.save_all_users({"alice": {"username": "alice"}})
        db.save_user_data("alice", "history.json", [{"id": "remove"}])
        db.save_all_users({})

        assert db.get_all_users() == {}
        assert not (tmp_path / "users" / "alice").exists()
        assert db.load_user_data("alice", "history.json", default=[]) == []


def test_sqlite_save_all_users_replaces_previous_user_snapshot(tmp_path):
    from utils.db import SQLiteBackend

    db = SQLiteBackend(tmp_path / "app.sqlite3")
    db.save_all_users({
        "alice": {"username": "alice", "tier": "free"},
        "bob": {"username": "bob", "tier": "pro"},
    })
    db.save_user_data("alice", "history.json", [{"id": "keep"}])
    db.save_user_data("bob", "history.json", [{"id": "remove"}])
    db.save_all_users({"alice": {"username": "alice", "tier": "team"}})

    assert db.get_all_users() == {"alice": {"username": "alice", "tier": "team"}}
    assert db.get_user("bob") is None
    assert db.load_user_data("alice", "history.json", default=[]) == [{"id": "keep"}]
    assert db.load_user_data("bob", "history.json", default=[]) == []


def test_sqlite_save_all_users_empty_snapshot_deletes_all_users(tmp_path):
    from utils.db import SQLiteBackend

    db = SQLiteBackend(tmp_path / "app.sqlite3")
    db.save_all_users({"alice": {"username": "alice"}})
    db.save_user_data("alice", "history.json", [{"id": "remove"}])
    db.save_all_users({})

    assert db.get_all_users() == {}
    assert db.load_user_data("alice", "history.json", default=[]) == []


def test_postgres_save_all_users_replaces_previous_user_snapshot():
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

    calls = connection.cursor_obj.calls
    assert calls[0] == ("DELETE FROM user_data WHERE username NOT IN (%s)", ("alice",))
    assert calls[1] == ("DELETE FROM users_db WHERE username NOT IN (%s)", ("alice",))
    assert "INSERT INTO users_db" in calls[2][0]
    assert calls[2][1] == ("alice", '{"username": "alice"}')
    assert connection.committed is True
    assert connection.closed is True
