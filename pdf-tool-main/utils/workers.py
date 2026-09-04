# -*- coding: utf-8 -*-
"""基于 QThread 的后台任务封装，避免 Qt UI 卡死。"""

from __future__ import annotations

import traceback
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from .errors import translate_error


class JobWorker(QThread):
    progress = Signal(str)
    succeeded = Signal(object)
    failed = Signal(str)
    finished_job = Signal()

    def __init__(
        self,
        job: Callable[[Callable[[str], None]], str],
        parent=None,
    ):
        super().__init__(parent)
        self._job = job

    def run(self):
        try:
            summary = self._job(self.progress.emit)
            self.succeeded.emit(summary or "操作完成")
        except Exception as exc:  # noqa: BLE001 - 统一错误出口
            detail = translate_error(exc)
            traceback.print_exc()
            self.failed.emit(detail)
        finally:
            self.finished_job.emit()
