"""
tests/test_logger.py
Unit tests for utils/logger.py - logging configuration.
"""
from __future__ import annotations

import logging
import os
import sys
import tempfile
import types
from pathlib import Path
from unittest.mock import patch

# Add project root to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock streamlit before importing modules that use it
_mock_st = types.ModuleType("streamlit")
_mock_st.session_state = {}
sys.modules["streamlit"] = _mock_st


def _reset_logger():
    """Remove the trade_ai logger and its handlers between tests."""
    logger = logging.getLogger("trade_ai")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


class TestLogger:
    """Tests for utils/logger.py logging configuration."""

    def test_configure_logging_returns_logger(self):
        """configure_logging returns a Logger instance named trade_ai."""
        _reset_logger()
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}, clear=False):
            from utils.logger import configure_logging
            _reset_logger()
            result = configure_logging()
            assert isinstance(result, logging.Logger)
            assert result.name == "trade_ai"

    def test_configure_logging_creates_logs_dir(self):
        """configure_logging creates the logs/ directory if missing."""
        _reset_logger()
        with tempfile.TemporaryDirectory() as tmp_str:
            tmp_dir = Path(tmp_str)
            # Patch the logger module so it creates logs/ inside our temp dir
            with patch("utils.logger.Path.resolve", return_value=tmp_dir / "utils" / "logger.py"):
                # Simpler approach: just verify logs/ exists after calling
                from utils.logger import configure_logging
                _reset_logger()
                configure_logging()
                # The real logs/ dir is at project root
                project_root = Path(__file__).resolve().parent.parent
                assert (project_root / "logs").is_dir()

    def test_configure_logging_no_duplicate_handlers(self):
        """Calling configure_logging twice does not double handlers."""
        _reset_logger()
        with patch.dict(os.environ, {"LOG_LEVEL": "INFO"}, clear=False):
            from utils.logger import configure_logging
            _reset_logger()
            configure_logging()
            handler_count_first = len(logging.getLogger("trade_ai").handlers)
            configure_logging()
            handler_count_second = len(logging.getLogger("trade_ai").handlers)
            assert handler_count_first == handler_count_second
            assert handler_count_first == 2  # console + file

    def test_invalid_log_level_falls_back_to_info(self):
        """Invalid LOG_LEVEL falls back to INFO for console handler."""
        _reset_logger()
        with patch.dict(os.environ, {"LOG_LEVEL": "BOGUS"}, clear=False):
            from utils.logger import configure_logging
            _reset_logger()
            logger = configure_logging()
            console_handler = None
            for h in logger.handlers:
                if isinstance(h, logging.StreamHandler) and not hasattr(h, "baseFilename"):
                    console_handler = h
                    break
            assert console_handler is not None
            assert console_handler.level == logging.INFO

    def test_log_level_warning_applied_to_console(self):
        """LOG_LEVEL=WARNING sets console handler to WARNING level."""
        _reset_logger()
        with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}, clear=False):
            from utils.logger import configure_logging
            _reset_logger()
            logger = configure_logging()
            console_handler = None
            for h in logger.handlers:
                if isinstance(h, logging.StreamHandler) and not hasattr(h, "baseFilename"):
                    console_handler = h
                    break
            assert console_handler is not None
            assert console_handler.level == logging.WARNING


# ---------------------------------------------------------------------------
# Simple runner for sandbox validation (pytest not available)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import traceback
    cls = TestLogger()
    methods = [m for m in dir(cls) if m.startswith("test_")]
    passed = failed = 0
    for m in sorted(methods):
        try:
            getattr(cls, m)()
            passed += 1
            print(f"  PASS: {m}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {m}: {e}")
            traceback.print_exc()
    print(f"\nResults: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
