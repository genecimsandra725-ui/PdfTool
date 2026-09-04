# -*- coding: utf-8 -*-
"""QFluentWidgets 版程序入口。"""

import sys

from PySide6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme

from ui.main_window import MainWindow
from utils.logger import setup_logging


def main():
    setup_logging()
    app = QApplication(sys.argv)
    setTheme(Theme.LIGHT)
    app.setApplicationName("PDF 工具")
    app.setOrganizationName("PDFTool")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
