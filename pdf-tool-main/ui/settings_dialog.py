# -*- coding: utf-8 -*-
"""程序设置对话框。"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout,
                               QLabel, QSpinBox, QVBoxLayout)
from qfluentwidgets import (BodyLabel, CheckBox, PrimaryPushButton,
                            PushButton)

from ui.common.notifications import toast
from utils.logger import export_log
from utils.settings import get_settings, save_settings


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("程序设置")
        self.setMinimumWidth(420)
        current = get_settings()
        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        self.auto_selftest = CheckBox("启动时自动运行环境自测")
        self.auto_selftest.setChecked(bool(current["auto_selftest_on_startup"]))
        layout.addWidget(self.auto_selftest)

        self.log_enabled = CheckBox("启用日志文件（logs/app.log）")
        self.log_enabled.setChecked(bool(current["log_to_file"]))
        layout.addWidget(self.log_enabled)

        size_row = QHBoxLayout()
        size_row.addWidget(BodyLabel("日志文件上限（MB）"))
        self.log_size = QSpinBox()
        self.log_size.setRange(1, 100)
        self.log_size.setValue(int(current.get("log_max_mb", 5) or 5))
        size_row.addWidget(self.log_size)
        size_row.addStretch(1)
        layout.addLayout(size_row)

        ui_title = QLabel("左侧标签页外观")
        ui_title.setStyleSheet("font-weight:bold;")
        layout.addWidget(ui_title)

        self.sidebar_width = self._spin_row(
            layout, "侧栏宽度（px）", int(current.get("sidebar_width", 160)),
            130, 260)
        self.nav_font_size = self._spin_row(
            layout, "标签字号", int(current.get("nav_font_size", 11)),
            9, 16)
        self.nav_padding_h = self._spin_row(
            layout, "标签左右内边距", int(current.get("nav_padding_h", 6)),
            0, 18)
        self.nav_padding_v = self._spin_row(
            layout, "标签上下内边距", int(current.get("nav_padding_v", 3)),
            0, 10)
        self.action_font_size = self._spin_row(
            layout, "设置/自测按钮字号", int(current.get("action_font_size", 10)),
            9, 16)
        self.action_height = self._spin_row(
            layout, "设置/自测按钮高度", int(current.get("action_height", 22)),
            18, 40)

        window_title = QLabel("窗口与页面布局")
        window_title.setStyleSheet("font-weight:bold;")
        layout.addWidget(window_title)

        self.window_width = self._spin_row(
            layout, "主窗口宽度", int(current.get("window_width", 940)),
            800, 1800)
        self.window_height = self._spin_row(
            layout, "主窗口高度", int(current.get("window_height", 620)),
            500, 1200)
        self.content_margin = self._spin_row(
            layout, "页面内容外边距", int(current.get("content_margin", 16)),
            6, 40)
        self.content_spacing = self._spin_row(
            layout, "页面内容间距", int(current.get("content_spacing", 6)),
            0, 18)
        self.log_height = self._spin_row(
            layout, "进度日志区高度", int(current.get("log_height", 92)),
            60, 220)

        export_row = QHBoxLayout()
        export_btn = PushButton("导出日志")
        save_btn = PrimaryPushButton("保存设置")
        export_row.addWidget(export_btn)
        export_row.addStretch(1)
        export_row.addWidget(save_btn)
        layout.addLayout(export_row)

        export_btn.clicked.connect(self._export_log)
        save_btn.clicked.connect(self._save)

    @staticmethod
    def _spin_row(layout, label, value, minimum, maximum):
        row = QHBoxLayout()
        row.addWidget(BodyLabel(label))
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(int(value))
        row.addWidget(spin)
        row.addStretch(1)
        layout.addLayout(row)
        return spin

    def _export_log(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", os.path.join(os.path.expanduser("~"),
                                          "pdf_tool_log.txt"),
            "文本文件 (*.txt);;所有文件 (*.*)")
        if not path:
            return
        try:
            target = export_log(path)
            toast(self, "完成", f"日志已导出：{target}", "success")
        except Exception as exc:
            toast(self, "失败", str(exc), "error")

    def _save(self):
        save_settings({
            "auto_selftest_on_startup": self.auto_selftest.isChecked(),
            "log_to_file": self.log_enabled.isChecked(),
            "log_max_mb": self.log_size.value(),
            "sidebar_width": self.sidebar_width.value(),
            "nav_font_size": self.nav_font_size.value(),
            "nav_padding_h": self.nav_padding_h.value(),
            "nav_padding_v": self.nav_padding_v.value(),
            "action_font_size": self.action_font_size.value(),
            "action_height": self.action_height.value(),
            "window_width": self.window_width.value(),
            "window_height": self.window_height.value(),
            "content_margin": self.content_margin.value(),
            "content_spacing": self.content_spacing.value(),
            "log_height": self.log_height.value(),
        })
        toast(self, "完成", "设置已保存到 settings.json", "success")
        self.accept()
