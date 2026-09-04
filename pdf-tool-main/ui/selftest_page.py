# -*- coding: utf-8 -*-
"""程序自测页面。"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QPlainTextEdit,
                               QVBoxLayout, QWidget)
from qfluentwidgets import (BodyLabel, PrimaryPushButton, PushButton,
                            SubtitleLabel)

from ui.common.notifications import toast
from utils.logger import export_log
from utils.selftest import risk_summary, run_selftest
from utils.workers import JobWorker


class SelfTestPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("selftest_page")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(8)
        self._layout = layout
        layout.addWidget(SubtitleLabel("程序自测"))
        layout.addWidget(BodyLabel(
            "检测 Python 依赖、Tesseract、LibreOffice、目录权限与环境风险点。"))

        self.result = QPlainTextEdit()
        self.result.setReadOnly(True)
        layout.addWidget(self.result, stretch=1)

        row = QHBoxLayout()
        self.run_btn = PrimaryPushButton("运行自测")
        self.export_btn = PushButton("导出日志")
        row.addWidget(self.run_btn)
        row.addWidget(self.export_btn)
        row.addStretch(1)
        layout.addLayout(row)
        self.run_btn.clicked.connect(self._run)
        self.export_btn.clicked.connect(self._export)

    def apply_page_layout(self, margin: int, spacing: int):
        vertical = max(2, margin * 2 // 3)
        self._layout.setContentsMargins(margin, vertical, margin, vertical)
        self._layout.setSpacing(spacing)

    def _run(self):
        self.run_btn.setEnabled(False)
        self.result.clear()
        worker = JobWorker(
            lambda progress: run_selftest(progress), self)
        worker.progress.connect(self._append)
        worker.succeeded.connect(self._finished)
        worker.failed.connect(
            lambda msg: toast(self, "失败", msg, "error"))
        worker.finished_job.connect(lambda: self.run_btn.setEnabled(True))
        worker.start()

    def _append(self, message: str):
        self.result.appendPlainText(message)

    def _finished(self, results):
        self.result.clear()
        for item in results:
            prefix = {"ok": "✓", "warning": "⚠", "error": "✕"}.get(
                item.status, "?")
            self.result.appendPlainText(
                f"{prefix} {item.title}：{item.message}")
        summary = risk_summary(results)
        self.result.appendPlainText("")
        self.result.appendPlainText(summary)
        if summary.startswith("未发现"):
            toast(self, "自测完成", summary, "success")
        else:
            toast(self, "自测完成", summary, "warning")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", os.path.join(os.path.expanduser("~"),
                                          "pdf_tool_log.txt"),
            "文本文件 (*.txt)")
        if not path:
            return
        try:
            target = export_log(path)
            toast(self, "完成", f"日志已导出：{target}", "success")
        except Exception as exc:
            toast(self, "失败", str(exc), "error")
