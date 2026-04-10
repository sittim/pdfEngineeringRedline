import logging
import sys

from qtpy.QtWidgets import QApplication

from pdfredline.app import MainWindow
from pdfredline.logging_setup import setup_logging


def main():
    log_path = setup_logging()
    print(f"Log file: {log_path}")

    app = QApplication(sys.argv)
    app.setApplicationName("PDF Redline")
    app.setOrganizationName("PDFRedline")

    logger = logging.getLogger("pdfredline.main")
    logger.info("Creating main window")
    window = MainWindow()
    window.set_log_path(log_path)
    window.show()
    logger.info("Entering Qt event loop")

    exit_code = app.exec()
    logger.info("Application exited with code %d", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
