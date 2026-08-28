"""Tests that storage isolation fixture works correctly."""
from __future__ import annotations

import pytest


def test_storage_redirected_to_isolated_directory(isolate_app_storage):
    """Storage operations write to isolated .pytest_tmp, not the real data/ directory."""
    from utils.storage import get_data_dir, save_json
    
    data_dir = get_data_dir()
    # Should be an isolated test directory
    assert ".pytest_tmp" in str(data_dir)
    assert "data" in str(data_dir).lower()
    
    # Write should succeed in isolated location
    save_json("test_isolation.json", {"isolated": True})
    assert (data_dir / "test_isolation.json").exists()


def test_db_singleton_reset_between_tests():
    """DB singleton is reset so each test gets a fresh backend."""
    import utils.db
    from utils.db import get_db
    
    # Singleton should be None at test start
    assert utils.db._db_instance is None
    
    # Get instance
    db = get_db()
    assert db is not None
    assert utils.db._db_instance is db
    
    # Fixture will reset it after this test


@pytest.mark.no_storage_isolation
def test_real_storage_directory_exists_when_isolation_skipped():
    """Marker no_storage_isolation allows accessing real data/ for validation."""
    from pathlib import Path
    from utils.storage import get_data_dir
    
    data_dir = get_data_dir()
    # Should resolve to real project data/ directory
    assert data_dir.exists()
    assert data_dir.is_dir()
    # Should not be a test isolation directory
    assert ".pytest_tmp" not in str(data_dir)
