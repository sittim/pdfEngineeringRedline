"""Per-session logging configuration.

Each invocation of the application creates a new timestamped log file in
``~/.pdfredline/logs/``. Uncaught Python exceptions, Qt warnings, and any
``logger.error()`` calls are mirrored to **both** the file and the terminal
(stderr) so they can be debugged from the command line.
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

    # Route uncaught Python exceptions through the logger so the full traceback
    # lands in BOTH the log file and the terminal.
    def _excepthook(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.getLogger("pdfredline").critical(
            "Uncaught exception", exc_info=(exc_type, exc_value, exc_tb)
        )

    sys.excepthook = _excepthook

    _install_qt_message_handler()

    logger = logging.getLogger("pdfredline")
    logger.info("=" * 60)
    logger.info("Session started — log file: %s", log_path)
    logger.info("Python: %s", sys.version.split()[0])
    logger.info("Platform: %s", sys.platform)
    logger.info("=" * 60)

    return log_path


def _install_qt_message_handler() -> None:
    """Forward Qt's own debug/warning/critical/fatal messages into Python logging.

    By default Qt writes its diagnostics to stderr through its C++ logging
    system, which bypasses Python's ``logging`` module entirely. That means
    things like 'QGraphicsItem::paint: ...' warnings would never make it to
    our log file. ``qInstallMessageHandler`` lets us intercept them and route
    them through the same handlers as everything else.
    """
    try:
        from qtpy.QtCore import QtMsgType, qInstallMessageHandler
    except ImportError:
        return

    qt_logger = logging.getLogger("Qt")

    level_map = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }

    def handler(msg_type, context, message):
        level = level_map.get(msg_type, logging.INFO)
        location = ""
        if context is not None:
            file = getattr(context, "file", None)
            line = getattr(context, "line", None)
            if file:
                location = f" ({file}:{line})"
        qt_logger.log(level, "%s%s", message, location)

    qInstallMessageHandler(handler)
