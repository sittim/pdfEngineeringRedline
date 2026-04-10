import os

import pytest
from qtpy.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Provide a QApplication instance for the entire test session."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def pytest_sessionfinish(session, exitstatus):
    """Force a clean exit to avoid PySide6 teardown segfault.

    PySide6 occasionally segfaults during interpreter shutdown when tearing
    down lingering QGraphicsItem / QGraphicsScene C++ objects after their
    Python wrappers have been collected. The tests have all reported their
    real status by the time this hook fires, so bypassing Python's normal
    exit machinery is safe and preserves the true exit code.

    We only short-circuit under CI (or when explicitly opted in) so local
    development still benefits from full coverage / atexit handlers.
    """
    if os.environ.get("CI") or os.environ.get("PYTEST_FORCE_EXIT"):
        os._exit(exitstatus)
