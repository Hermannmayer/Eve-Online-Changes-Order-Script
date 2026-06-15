"""
EVE Online 价格监控 - PySide6 主入口
"""

import sys
import logging

from PySide6.QtWidgets import QApplication

from src.config import Config
from src.gui.app import MainWindow

logger = logging.getLogger(__name__)


def setup_logging():
    """配置日志"""
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(console)

    file_handler = logging.FileHandler("eve_price_monitor.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)

    return logger


def main():
    """主入口"""
    setup_logging()

    app = QApplication(sys.argv)
    app.setApplicationName("EVE 价格监控")

    config = Config()
    if not config.load():
        print("首次运行，创建默认配置文件 config.yaml")
        config.save()

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
