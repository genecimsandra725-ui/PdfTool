# -*- coding: utf-8 -*-
"""统一 Qt 消息提示封装。"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget
from qfluentwidgets import InfoBar, InfoBarPosition


def toast(parent: QWidget, title: str, message: str,
          kind: str = "success"):
    position = InfoBarPosition.TOP_RIGHT
    if kind == "error":
        InfoBar.error(title, message, parent=parent,
                      position=position, duration=6000)
    elif kind == "warning":
        InfoBar.warning(title, message, parent=parent,
                        position=position, duration=5000)
    else:
        InfoBar.success(title, message, parent=parent,
                        position=position, duration=4000)


def confirm(parent: QWidget, title: str, message: str) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.No)
    return box.exec() == QMessageBox.Yes
