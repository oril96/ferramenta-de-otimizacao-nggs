import logging
import os
from logging.handlers import RotatingFileHandler

from PyQt6 import QtWidgets

from src.ui.main_window import MainWindow
from src.ui.theme import DARK_MODERN_QSS


def setup_logging() -> None:
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    file_handler = RotatingFileHandler("logs/optimus.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)


def main() -> int:
    setup_logging()
    app = QtWidgets.QApplication([])
    app.setStyleSheet(DARK_MODERN_QSS)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
