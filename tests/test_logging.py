import logging
from pathlib import Path

from pdfredline import logging_setup as ls


def test_setup_creates_timestamped_log_file(tmp_path):
    original_dir = ls.LOG_DIR
    ls.LOG_DIR = tmp_path / "logs"
    try:
        log_path = ls.setup_logging()
        assert log_path.exists()
        assert log_path.name.startswith("session_")
        assert log_path.name.endswith(".log")
        assert log_path.parent == ls.LOG_DIR
    finally:
        ls.LOG_DIR = original_dir


def test_logged_messages_appear_in_file(tmp_path):
    original_dir = ls.LOG_DIR
    ls.LOG_DIR = tmp_path / "logs"
    try:
        log_path = ls.setup_logging()
        logger = logging.getLogger("pdfredline.test")
        logger.info("Hello from test")
        logger.error("Test error message")

        for h in logging.getLogger().handlers:
            h.flush()

        content = log_path.read_text()
        assert "Hello from test" in content
        assert "Test error message" in content
        assert "Session started" in content
    finally:
        ls.LOG_DIR = original_dir


def test_log_dir_default_is_home():
    expected = Path.home() / ".pdfredline" / "logs"
    assert expected == ls.LOG_DIR
