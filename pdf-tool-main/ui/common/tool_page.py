# -*- coding: utf-8 -*-
"""通用工具页：文件选择、输出路径、参数表单、后台执行、日志。"""

from __future__ import annotations

import os
from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFileDialog,
                               QHBoxLayout, QLabel, QLineEdit,
                               QPlainTextEdit, QPushButton, QSpinBox,
                               QVBoxLayout, QWidget)
from qfluentwidgets import (BodyLabel, CheckBox, LineEdit, PrimaryPushButton,
                            PushButton, RadioButton, SubtitleLabel)

from ui.common.job_page import JobPage
from ui.common.notifications import toast
from utils.errors import translate_error
from utils.workers import JobWorker


class ToolPage(JobPage):
    """支持多文件/单文件、输出目录或输出文件、日志与后台任务的工具页。"""

    def __init__(self, title: str, description: str,
                 exts=(".pdf",), output_kind: str = "dir",
                 object_name: str = "", single_mode: bool = False):
        super().__init__(title, description, object_name or title)
        self.exts = tuple(exts)
        self.output_kind = output_kind
        self.single_mode = single_mode
        self.file_paths: list[str] = []
        self.setAcceptDrops(True)

        input_box = QVBoxLayout()
        input_box.setContentsMargins(0, 2, 0, 2)
        input_box.setSpacing(2)
        self.add_btn = QPushButton("＋")
        self.add_btn.setFixedSize(92, 92)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;"
            "color:#0ea5e9;font-size:44px;font-weight:200;}"
            "QPushButton:hover{color:#0284c7;background:#e0f2fe;"
            "border-radius:46px;}")
        self.file_count = BodyLabel("")
        self.file_count.setAlignment(Qt.AlignCenter)
        self.file_count.setStyleSheet("color:#94a3b8;font-size:12px;")
        input_box.addWidget(self.add_btn, 0, Qt.AlignHCenter)
        input_box.addWidget(self.file_count, 0, Qt.AlignHCenter)
        self.content.addLayout(input_box)

        output_row = QHBoxLayout()
        output_row.addWidget(BodyLabel("输出路径"))
        self.output_edit = LineEdit()
        self.output_edit.setPlaceholderText(
            "选择输出文件夹" if output_kind == "dir" else "选择输出 PDF 文件")
        output_row.addWidget(self.output_edit, stretch=1)
        self.output_btn = PushButton("选择")
        output_row.addWidget(self.output_btn)
        output_widget = QWidget()
        output_widget.setLayout(output_row)
        self.content.addWidget(output_widget)

        self.options_box = QVBoxLayout()
        self.content.addLayout(self.options_box)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(92)
        self.content.addWidget(self.log_view)

        action_row = QHBoxLayout()
        self.run_btn = PrimaryPushButton("开始")
        self.open_btn = PushButton("打开输出位置")
        self.open_btn.setEnabled(False)
        action_row.addWidget(self.run_btn)
        action_row.addWidget(self.open_btn)
        action_row.addStretch(1)
        self.content.addLayout(action_row)

        self.add_btn.clicked.connect(self._pick_files)
        self.output_btn.clicked.connect(self._pick_output)
        self.run_btn.clicked.connect(self._start)
        self.open_btn.clicked.connect(self._open_output)

    def _on_dropped_files(self, paths):
        valid = [p for p in paths
                 if os.path.isfile(p) and p.lower().endswith(self.exts)]
        if self.single_mode:
            valid = valid[:1]
        self.add_files(valid)
        if not valid:
            toast(self, "提示", "拖入的文件类型不受支持", "warning")

    # 文件选择 ──────────────────────────────────────────────
    def _pattern(self) -> str:
        return " ".join(f"*{ext}" for ext in self.exts)

    def _pick_files(self):
        if self.single_mode:
            path, _ = QFileDialog.getOpenFileName(
                self, "选择文件", "", f"支持文件 ({self._pattern()})")
            paths = [path] if path else []
        else:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "选择文件", "", f"支持文件 ({self._pattern()})")
        self.add_files(paths)

    def add_files(self, paths: list[str]):
        if self.single_mode:
            self.file_paths.clear()
        for path in paths:
            norm = os.path.normpath(path)
            if norm not in self.file_paths:
                self.file_paths.append(norm)
        self._refresh_file_count()

    def _refresh_file_count(self):
        count = len(self.file_paths)
        if count == 0:
            self.file_count.setText("")
        elif self.single_mode:
            self.file_count.setText(os.path.basename(self.file_paths[0]))
        else:
            self.file_count.setText(f"已选择 {count} 个文件")

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [url.toLocalFile() for url in event.mimeData().urls()
                 if url.isLocalFile()]
        valid = [p for p in paths
                 if os.path.isfile(p) and p.lower().endswith(self.exts)]
        self.add_files(valid)
        if not valid:
            toast(self, "提示", "拖入的文件类型不受支持", "warning")

    def _pick_output(self):
        if self.output_kind == "dir":
            path = QFileDialog.getExistingDirectory(
                self, "选择输出文件夹", self.output_edit.text() or "")
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "选择输出文件", self.output_edit.text() or "output.pdf",
                "PDF 文件 (*.pdf)")
        if path:
            self.output_edit.setText(path)

    # 表单 ─────────────────────────────────────────────────
    def add_row(self, label: str, widget: QWidget):
        row = QHBoxLayout()
        row.addWidget(BodyLabel(label))
        row.addWidget(widget)
        row.addStretch(1)
        self.options_box.addLayout(row)

    def apply_page_layout(self, margin: int, spacing: int,
                          log_height: int = 92):
        super().apply_page_layout(margin, spacing)
        self.log_view.setMaximumHeight(int(log_height))

    def _start(self):
        if not self.file_paths:
            toast(self, "提示", "请先添加输入文件", "warning")
            return
        output = self.output_edit.text().strip()
        if not output:
            toast(self, "提示", "请设置输出路径", "warning")
            return
        try:
            job = self.make_job(list(self.file_paths), output)
        except Exception as exc:
            toast(self, "失败", translate_error(exc), "error")
            return
        self.run_job(job)

    def make_job(self, paths, output) -> Callable[[Callable[[str], None]], str]:
        raise NotImplementedError

    # 状态 ─────────────────────────────────────────────────
    def on_progress(self, message: str):
        self.log_view.appendPlainText(message)

    def on_busy(self, busy: bool, message: str = ""):
        self.run_btn.setEnabled(not busy)
        self.add_btn.setEnabled(not busy)
        self.output_btn.setEnabled(not busy)
        if busy:
            self.open_btn.setEnabled(False)
            self.log_view.appendPlainText(message)
        else:
            self.open_btn.setEnabled(self.file_paths and bool(
                self.output_edit.text()))

    def _open_output(self):
        path = self.output_edit.text()
        if not path:
            return
        if os.path.isfile(path):
            path = os.path.dirname(path)
        if os.path.isdir(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))


def make_checkbox(default: bool = False) -> CheckBox:
    box = CheckBox()
    box.setChecked(default)
    return box


def make_combo(values, default=None) -> QComboBox:
    combo = QComboBox()
    combo.addItems(values)
    if default and default in values:
        combo.setCurrentText(default)
    return combo


def make_spin(default=1, minimum=1, maximum=9999) -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(default)
    return spin


def make_double_spin(default=0.0, minimum=0.0, maximum=200.0,
                     decimals=1) -> QDoubleSpinBox:
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setValue(default)
    return spin
