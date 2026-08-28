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


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "no_storage_isolation: skip the autouse storage isolation fixture"
    )
