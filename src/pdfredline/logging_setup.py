"""Per-session logging configuration.

Each invocation of the application creates a new timestamped log file in
``~/.pdfredline/logs/``. Uncaught exceptions are routed to the same log so
issues can be diagnosed after the fact.
"""
from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path.home() / ".pdfredline" / "logs"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(level: int = logging.INFO) -> Path:
    """Configure root logging for this session.

    Returns the path of the log file created for this session.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_path = LOG_DIR / f"session_{timestamp}.log"

    file_handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    root.setLevel(level)
    # Replace any pre-existing handlers (e.g. from a prior call in the same process)
    root.handlers = [file_handler, stream_handler]

    # Route uncaught exceptions through the logger
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("pdfredline").critical(
            "Uncaught exception", exc_info=(exc_type, exc_value, exc_tb)
        )

    sys.excepthook = _excepthook

    logger = logging.getLogger("pdfredline")
    logger.info("=" * 60)
    logger.info("Session started — log file: %s", log_path)
    logger.info("Python: %s", sys.version.split()[0])
    logger.info("Platform: %s", sys.platform)
    logger.info("=" * 60)

    return log_path
