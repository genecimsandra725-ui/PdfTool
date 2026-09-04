# -*- coding: utf-8 -*-
"""需要列表/文本编辑的专用页面：页面排序、遮盖区域。"""

from __future__ import annotations

import os

from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLineEdit,
                               QInputDialog, QListWidget, QPlainTextEdit,
                               QVBoxLayout)
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from qfluentwidgets import (BodyLabel, LineEdit, PrimaryPushButton,
                            PushButton, SubtitleLabel)

from services import overlay_service, pdf_service
from ui.common.job_page import JobPage
from ui.common.notifications import toast
from utils.workers import JobWorker


class _PathRow(QHBoxLayout):
    def __init__(self, browse_text: str = "选择"):
        super().__init__()
        self.edit = LineEdit()
        self.btn = PushButton(browse_text)
        self.addWidget(self.edit, stretch=1)
        self.addWidget(self.btn)


class ReorderPage(JobPage):
    """页面排序页：查看页序、上移/下移/复制/删除后保存。"""

    def __init__(self):
        super().__init__(
            "页面排序", "调整 PDF 页面顺序，可复制或删除页面。",
            object_name="reorder_pages")
        self.order: list[int] = []

        self.src_row = _PathRow("打开 PDF")
        self.content.addLayout(self.src_row)

        self.page_list = QListWidget()
        self.page_list.setMinimumHeight(160)
        self.content.addWidget(self.page_list)

        btn_row = QHBoxLayout()
        actions = [
            ("上移", self._up), ("下移", self._down),
            ("复制页面", self._duplicate), ("删除页面", self._delete),
            ("重置顺序", self._reset),
        ]
        for text, func in actions:
            btn = PushButton(text)
            btn.clicked.connect(func)
            btn_row.addWidget(btn)
        btn_row.addStretch(1)
        self.content.addLayout(btn_row)

        self.out_row = _PathRow("保存为")
        self.content.addLayout(self.out_row)

        action = QHBoxLayout()
        self.run_btn = PrimaryPushButton("保存 PDF")
        self.open_btn = PushButton("打开输出位置")
        self.open_btn.setEnabled(False)
        action.addWidget(self.run_btn)
        action.addWidget(self.open_btn)
        action.addStretch(1)
        self.content.addLayout(action)

        self.src_row.btn.clicked.connect(self._pick_src)
        self.out_row.btn.clicked.connect(self._pick_out)
        self.run_btn.clicked.connect(self._start)
        self.open_btn.clicked.connect(self._open_out)

    def _pick_src(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 PDF", "",
                                              "PDF 文件 (*.pdf)")
        if path:
            self.src_row.edit.setText(path)
            self.order = list(range(pdf_service.page_count(path)))
            self._refresh()

    def _pick_out(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF", self.out_row.edit.text() or "reordered.pdf",
            "PDF 文件 (*.pdf)")
        if path:
            self.out_row.edit.setText(path)

    def _refresh(self):
        self.page_list.clear()
        for idx, orig in enumerate(self.order):
            self.page_list.addItem(f"{idx + 1}. 第 {orig + 1} 页")

    def _selected(self):
        return self.page_list.currentRow()

    def _up(self):
        i = self._selected()
        if i <= 0:
            return
        self.order[i - 1], self.order[i] = self.order[i], self.order[i - 1]
        self._refresh()
        self.page_list.setCurrentRow(i - 1)

    def _down(self):
        i = self._selected()
        if i < 0 or i >= len(self.order) - 1:
            return
        self.order[i], self.order[i + 1] = self.order[i + 1], self.order[i]
        self._refresh()
        self.page_list.setCurrentRow(i + 1)

    def _duplicate(self):
        i = self._selected()
        if i >= 0:
            self.order.insert(i + 1, self.order[i])
            self._refresh()
            self.page_list.setCurrentRow(i + 1)

    def _delete(self):
        i = self._selected()
        if i < 0:
            return
        if len(self.order) <= 1:
            toast(self, "提示", "不能删除最后一页", "warning")
            return
        self.order.pop(i)
        self._refresh()

    def _reset(self):
        if self.src_row.edit.text():
            self.order = list(range(pdf_service.page_count(
                self.src_row.edit.text())))
            self._refresh()

    def _start(self):
        src = self.src_row.edit.text().strip()
        out = self.out_row.edit.text().strip()
        if not src or not out:
            toast(self, "提示", "请先选择 PDF 与输出路径", "warning")
            return
        order = list(self.order)

        def job(progress):
            return pdf_service.reorder_pdf(src, out, order, progress)

        self._launch(job)

    def _launch(self, job):
        worker = JobWorker(job, self)
        worker.progress.connect(self.on_progress)
        worker.succeeded.connect(
            lambda msg: toast(self, "完成", msg, "success"))
        worker.succeeded.connect(lambda _: self.open_btn.setEnabled(True))
        worker.failed.connect(
            lambda msg: toast(self, "失败", msg, "error"))
        worker.finished_job.connect(
            lambda: self.run_btn.setEnabled(True))
        self.run_btn.setEnabled(False)
        worker.start()

    def _open_out(self):
        path = self.out_row.edit.text()
        if os.path.isfile(path):
            path = os.path.dirname(path)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def on_progress(self, message: str):
        toast(self, "进度", message, "success")


class RedactPage(JobPage):
    """遮盖敏感内容页：每行一个区域。"""

    def __init__(self):
        super().__init__(
            "遮盖敏感内容",
            "每行填写：页码,X(mm),Y(mm),宽(mm),高(mm)。坐标从页面左上角开始。",
            object_name="redact_pdf")
        self.src_row = _PathRow("打开 PDF")
        self.content.addLayout(self.src_row)
        self.region_edit = QPlainTextEdit()
        self.region_edit.setPlaceholderText("例如：\n1,10,10,80,20\n2,5,5,50,10")
        self.region_edit.setMaximumHeight(120)
        self.content.addWidget(self.region_edit)
        self.out_row = _PathRow("保存为")
        self.content.addLayout(self.out_row)
        action = QHBoxLayout()
        self.run_btn = PrimaryPushButton("应用遮盖")
        self.open_btn = PushButton("打开输出位置")
        self.open_btn.setEnabled(False)
        action.addWidget(self.run_btn)
        action.addWidget(self.open_btn)
        action.addStretch(1)
        self.content.addLayout(action)

        self.src_row.btn.clicked.connect(self._pick_src)
        self.out_row.btn.clicked.connect(self._pick_out)
        self.run_btn.clicked.connect(self._start)
        self.open_btn.clicked.connect(
            lambda: self._open_out(self.out_row.edit.text()))

    def _pick_src(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 PDF", "",
                                              "PDF 文件 (*.pdf)")
        if path:
            self.src_row.edit.setText(path)

    def _pick_out(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF", self.out_row.edit.text() or "redacted.pdf",
            "PDF 文件 (*.pdf)")
        if path:
            self.out_row.edit.setText(path)

    def _parse_regions(self):
        regions = []
        for line_no, line in enumerate(self.region_edit.toPlainText()
                                       .splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.replace("，", ",").split(",")]
            if len(parts) != 5:
                raise ValueError(f"第 {line_no} 行格式不正确")
            regions.append(tuple(float(part) if i else int(part)
                                 for i, part in enumerate(parts)))
        return regions

    def _start(self):
        src = self.src_row.edit.text().strip()
        out = self.out_row.edit.text().strip()
        if not src or not out:
            toast(self, "提示", "请先选择 PDF 与输出路径", "warning")
            return
        try:
            regions = self._parse_regions()
        except ValueError as exc:
            toast(self, "格式错误", str(exc), "error")
            return

        def job(progress):
            return overlay_service.apply_redaction(
                src, out, regions, progress)

        worker = JobWorker(job, self)
        worker.progress.connect(self.on_progress)
        worker.succeeded.connect(
            lambda msg: toast(self, "完成", msg, "success"))
        worker.succeeded.connect(lambda _: self.open_btn.setEnabled(True))
        worker.failed.connect(
            lambda msg: toast(self, "失败", msg, "error"))
        worker.finished_job.connect(lambda: self.run_btn.setEnabled(True))
        self.run_btn.setEnabled(False)
        worker.start()

    def on_progress(self, message: str):
        pass

    @staticmethod
    def _open_out(path: str):
        if not path:
            return
        if os.path.isfile(path):
            path = os.path.dirname(path)
        if path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

class BookmarksPage(JobPage):
    """书签页：查看、添加、删除书签并保存，或按一级书签拆分。"""

    def __init__(self):
        super().__init__(
            "书签", "查看、添加、删除 PDF 书签，也可按一级书签拆分。",
            object_name="bookmarks")
        self._flat: list[tuple[int, str, int]] = []
        self._src = ""

        self.src_row = _PathRow("打开 PDF")
        self.content.addLayout(self.src_row)
        self.bookmark_list = QListWidget()
        self.bookmark_list.setMinimumHeight(160)
        self.content.addWidget(self.bookmark_list)

        edit_row = QHBoxLayout()
        add_btn = PushButton("添加书签")
        delete_btn = PushButton("删除所选")
        edit_row.addWidget(add_btn)
        edit_row.addWidget(delete_btn)
        edit_row.addStretch(1)
        self.content.addLayout(edit_row)

        self.out_row = _PathRow("保存书签文件")
        self.content.addLayout(self.out_row)
        self.split_dir = _PathRow("按书签拆分的输出文件夹")
        self.content.addLayout(self.split_dir)

        action = QHBoxLayout()
        self.save_btn = PrimaryPushButton("保存书签")
        self.split_btn = PrimaryPushButton("按书签拆分")
        self.open_btn = PushButton("打开输出位置")
        self.open_btn.setEnabled(False)
        action.addWidget(self.save_btn)
        action.addWidget(self.split_btn)
        action.addWidget(self.open_btn)
        action.addStretch(1)
        self.content.addLayout(action)

        self.src_row.btn.clicked.connect(self._pick_src)
        self.out_row.btn.clicked.connect(self._pick_save)
        self.split_dir.btn.clicked.connect(self._pick_split_dir)
        add_btn.clicked.connect(self._add)
        delete_btn.clicked.connect(self._delete)
        self.save_btn.clicked.connect(self._save)
        self.split_btn.clicked.connect(self._split)

    def _pick_src(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 PDF", "",
                                              "PDF 文件 (*.pdf)")
        if path:
            self._src = path
            self.src_row.edit.setText(path)
            self._flat, _ = pdf_service.read_bookmarks(path)
            self._refresh()

    def _refresh(self):
        self.bookmark_list.clear()
        for indent, title, page in self._flat:
            prefix = "    " * indent
            self.bookmark_list.addItem(
                f"{prefix}▸ {title}（第 {page + 1} 页）")

    def _add(self):
        if not self._src:
            toast(self, "提示", "请先打开 PDF", "warning")
            return
        title, ok = QInputDialog.getText(self, "添加书签", "书签标题：")
        if not ok or not title:
            return
        page_str, ok = QInputDialog.getText(self, "添加书签", "页码：")
        if not ok or not page_str.isdigit():
            return
        page = int(page_str) - 1
        if page < 0:
            return
        self._flat.append((0, title, page))
        self._refresh()

    def _delete(self):
        row = self.bookmark_list.currentRow()
        if row >= 0 and row < len(self._flat):
            self._flat.pop(row)
            self._refresh()

    def _pick_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存书签 PDF",
            self.out_row.edit.text() or "bookmarked.pdf",
            "PDF 文件 (*.pdf)")
        if path:
            self.out_row.edit.setText(path)

    def _pick_split_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "选择输出文件夹", self.split_dir.edit.text() or "")
        if path:
            self.split_dir.edit.setText(path)

    def _save(self):
        if not self._src or not self.out_row.edit.text().strip():
            toast(self, "提示", "请选择 PDF 并设置保存路径", "warning")
            return
        flat = list(self._flat)
        out = self.out_row.edit.text().strip()

        def job(progress):
            return pdf_service.save_bookmarks(
                self._src, out, flat, progress)

        self._launch_custom(job)

    def _split(self):
        if not self._src or not self.split_dir.edit.text().strip():
            toast(self, "提示", "请选择 PDF 与输出文件夹", "warning")
            return
        outdir = self.split_dir.edit.text().strip()

        def job(progress):
            return pdf_service.split_by_bookmarks(
                self._src, outdir, progress)

        self._launch_custom(job)

    def _launch_custom(self, job):
        worker = JobWorker(job, self)
        worker.progress.connect(self.on_progress)
        worker.succeeded.connect(
            lambda msg: toast(self, "完成", msg, "success"))
        worker.succeeded.connect(lambda _: self.open_btn.setEnabled(True))
        worker.failed.connect(
            lambda msg: toast(self, "失败", msg, "error"))
        worker.finished_job.connect(
            lambda: (self.save_btn.setEnabled(True),
                     self.split_btn.setEnabled(True)))
        self.save_btn.setEnabled(False)
        self.split_btn.setEnabled(False)
        worker.start()

    def on_progress(self, message: str):
        pass


def custom_pdf_pages():
    return [ReorderPage(), RedactPage(), BookmarksPage(), MetadataPage()]


class MetadataPage(JobPage):
    """元数据页：打开 PDF 自动读取字段，修改后保存。"""

    def __init__(self):
        super().__init__(
            "元数据", "查看并编辑 PDF 标题、作者、主题等元数据。",
            object_name="metadata_page")
        self._fields: dict[str, QLineEdit] = {}
        self.src_row = _PathRow("打开 PDF")
        self.content.addLayout(self.src_row)

        info_label = BodyLabel("打开 PDF 后自动读取以下字段。")
        self.content.addWidget(info_label)

        for _key, label in pdf_service.METADATA_FIELDS:
            row = QHBoxLayout()
            edit = LineEdit()
            row.addWidget(BodyLabel(label))
            row.addWidget(edit, stretch=1)
            self._fields[_key] = edit
            self.content.addLayout(row)

        self.out_row = _PathRow("保存为")
        self.content.addLayout(self.out_row)
        action = QHBoxLayout()
        self.run_btn = PrimaryPushButton("保存元数据")
        action.addWidget(self.run_btn)
        action.addStretch(1)
        self.content.addLayout(action)

        self.src_row.btn.clicked.connect(self._pick_src)
        self.out_row.btn.clicked.connect(self._pick_out)
        self.run_btn.clicked.connect(self._save)

    def _pick_src(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择 PDF", "",
                                              "PDF 文件 (*.pdf)")
        if path:
            self.src_row.edit.setText(path)
            try:
                fields, _pages = pdf_service.metadata_fields(path)
                for key, edit in self._fields.items():
                    edit.setText(fields.get(key, ""))
            except Exception as exc:
                toast(self, "读取失败", str(exc), "error")

    def _pick_out(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存 PDF", self.out_row.edit.text() or "metadata.pdf",
            "PDF 文件 (*.pdf)")
        if path:
            self.out_row.edit.setText(path)

    def _save(self):
        src = self.src_row.edit.text().strip()
        out = self.out_row.edit.text().strip()
        if not src or not out:
            toast(self, "提示", "请选择 PDF 与输出路径", "warning")
            return
        fields = {key: edit.text() for key, edit in self._fields.items()}

        def job(progress):
            return pdf_service.save_metadata(src, out, fields, progress)

        worker = JobWorker(job, self)
        worker.succeeded.connect(
            lambda msg: toast(self, "完成", msg, "success"))
        worker.failed.connect(
            lambda msg: toast(self, "失败", msg, "error"))
        worker.finished_job.connect(lambda: self.run_btn.setEnabled(True))
        self.run_btn.setEnabled(False)
        worker.start()
