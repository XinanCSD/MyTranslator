import logging
import sys

from PySide6.QtWidgets import QApplication

from config import LOG_DIR
from main_window import MainWindow


def setup_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def main():
    setup_logging()
    logging.getLogger(__name__).info("Application starting")
    app = QApplication(sys.argv)
    app.setApplicationName("MyTranslator")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
