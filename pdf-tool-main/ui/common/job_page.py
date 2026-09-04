# -*- coding: utf-8 -*-
"""后台任务页面基础组件。"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QVBoxLayout, QWidget)
from qfluentwidgets import (BodyLabel, PrimaryPushButton, PushButton,
                            SubtitleLabel)

from ui.common.notifications import toast
from utils.workers import JobWorker


class JobPage(QWidget):
    """统一承载标题、说明、后台任务执行与通知的页面。"""

    def __init__(self, title: str, description: str = "",
                 object_name: str = ""):
        super().__init__()
        self.setObjectName(object_name or title)
        self.title = title
        self._workers: list[JobWorker] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 10, 16, 10)
        root.setSpacing(6)
        self._root_layout = root

        head = QVBoxLayout()
        head.setSpacing(2)
        head.addWidget(SubtitleLabel(title))
        if description:
            body = BodyLabel(description)
            body.setWordWrap(True)
            head.addWidget(body)
        root.addLayout(head)

        self.content = QVBoxLayout()
        root.addLayout(self.content, stretch=1)
        self.content.setSpacing(6)
        self._content_layout = self.content

    def apply_page_layout(self, margin: int, spacing: int):
        vertical = max(2, margin * 2 // 3)
        self._root_layout.setContentsMargins(margin, vertical, margin, vertical)
        self._root_layout.setSpacing(spacing)
        self._content_layout.setSpacing(spacing)

    def run_job(self, job: Callable[[Callable[[str], None]], str],
                busy_text: str = "正在处理，请稍候…"):
        worker = JobWorker(job, self)
        worker.progress.connect(lambda msg: self.on_progress(msg))
        worker.succeeded.connect(
            lambda msg: toast(self, "完成", msg, "success"))
        worker.failed.connect(
            lambda msg: toast(self, "失败", msg, "error"))
        worker.finished_job.connect(lambda: self._release(worker))
        self._workers.append(worker)
        self.on_busy(True, busy_text)
        worker.start()

    def on_progress(self, message: str):
        """子类可覆写，用于状态栏/日志展示。"""

    def on_busy(self, busy: bool, message: str = ""):
        """子类可覆写，用于按钮禁用状态。"""

    def _release(self, worker: JobWorker):
        if worker in self._workers:
            self._workers.remove(worker)
        self.on_busy(False)


class FileListCard(QWidget):
    """文件列表：选择、移除、清空，Qt 原生拖放支持。"""

    def __init__(self, label: str = "输入文件", exts=(".pdf",)):
        super().__init__()
        self.exts = tuple(exts)
        self.setAcceptDrops(True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 12)
        outer.addWidget(BodyLabel(label))

        row = QHBoxLayout()
        self.add_btn = PushButton("选择文件")
        self.clear_btn = PushButton("清空")
        row.addWidget(self.add_btn)
        row.addStretch(1)
        row.addWidget(self.clear_btn)
        outer.addLayout(row)
