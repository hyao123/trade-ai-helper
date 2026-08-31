"""Pytest configuration and shared fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_app_storage(request, monkeypatch):
    """Redirect all tests to use isolated test storage, avoiding real data/ pollution.
    
    Patches:
    - utils.storage.get_data_dir -> .pytest_tmp/<test_name>/data
    - DATABASE_URL and SQLITE_DB_PATH environment variables cleared
    - utils.db singleton reset before and after each test
    
    Tests marked with @pytest.mark.no_storage_isolation skip this fixture.
    """
    # Skip if test is marked no_storage_isolation
    marker = request.node.get_closest_marker("no_storage_isolation")
    if marker:
        yield None
        return
    
    # Create isolated directory in .pytest_tmp
    test_name = request.node.name
    test_root = Path(".pytest_tmp") / test_name
    test_root.mkdir(parents=True, exist_ok=True)
    test_data_dir = test_root / "data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Patch get_data_dir
    monkeypatch.setattr("utils.storage.get_data_dir", lambda: test_data_dir)
    
    # Clear database environment variables
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SQLITE_DB_PATH", raising=False)
    
    # Reset DB singleton
    import utils.db
    utils.db._db_instance = None
    utils.db._db_signature = None
    
    yield test_data_dir
    
    # Reset DB singleton after test
    utils.db._db_instance = None
    utils.db._db_signature = None
    
    # Cleanup is optional; .pytest_tmp is gitignored


@pytest.fixture(autouse=True)
def redirect_system_temp(monkeypatch):
    """Make ``tempfile`` sandbox-safe by pointing it at the workspace.

    The DSH Windows sandbox denies both reads/writes to the OS temp area AND
    the ``chmod(..., follow_symlinks=False)`` call that
    ``tempfile.TemporaryDirectory`` performs during cleanup (WinError 5). That
    made every test using ``TemporaryDirectory``/``mkdtemp`` fail or hang
    (observed in test_email_gate, test_user_prefs, test_utils, ...).

    This fixture patches:
    - ``tempfile.TemporaryDirectory`` -> workspace-based replacement that never
      chmods and cleans up with ``rmtree(ignore_errors=True)``;
    - ``tempfile.mkdtemp`` -> same workspace-based behavior;
    - ``tempfile.tempdir`` + TEMP/TMP/TMPDIR env vars -> workspace dir, so
      ``NamedTemporaryFile`` and subprocesses also stay inside the workspace.

    All patches are reverted by monkeypatch after each test.
    """
    import shutil
    import tempfile
    import uuid

    workspace_temp = Path(".pytest_tmp") / "_sys_temp"
    workspace_temp.mkdir(parents=True, exist_ok=True)

    def _make_dir(prefix="tmp", suffix="", dir=None):
        base = Path(dir) if dir else workspace_temp
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"{prefix}{uuid.uuid4().hex}{suffix}"
        path.mkdir()
        return str(path)

    class _WorkspaceTemporaryDirectory:
        """Drop-in for tempfile.TemporaryDirectory with sandbox-safe cleanup."""

        def __init__(self, suffix="", prefix="tmp", dir=None, *args, **kwargs):
            self._path = _make_dir(prefix, suffix, dir)
            self.name = self._path

        def __enter__(self):
            return self.name

        def __exit__(self, exc_type, exc, tb):
            self.cleanup()

        def cleanup(self):
            shutil.rmtree(self._path, ignore_errors=True)

    monkeypatch.setattr(tempfile, "TemporaryDirectory", _WorkspaceTemporaryDirectory)
    monkeypatch.setattr(tempfile, "mkdtemp", _make_dir)
    monkeypatch.setattr(tempfile, "tempdir", str(workspace_temp))
    monkeypatch.setenv("TEMP", str(workspace_temp))
    monkeypatch.setenv("TMP", str(workspace_temp))
    monkeypatch.setenv("TMPDIR", str(workspace_temp))
    yield workspace_temp


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "no_storage_isolation: skip the autouse storage isolation fixture"
    )
