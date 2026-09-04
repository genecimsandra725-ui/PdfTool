# -*- coding: utf-8 -*-
"""QFluentWidgets 主窗口：紧凑单列表侧栏 + 右侧页面。"""

from __future__ import annotations

from PySide6.QtCore import (QEasingCurve, QParallelAnimationGroup,
                            QPoint, QPropertyAnimation, QSize, QTimer, Qt)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QScrollArea,
                               QStackedWidget, QToolButton, QVBoxLayout,
                               QWidget)
from qfluentwidgets import FluentIcon, PushButton, SubtitleLabel

from ui.common.notifications import toast
from ui.pages.custom_pages import custom_pdf_pages
from ui.pages.document_convert import doc_conversion_pages
from ui.pages.pdf_tools import pdf_tool_pages
from ui.selftest_page import SelfTestPage
from ui.settings_dialog import SettingsDialog
from utils.logger import get_logger
from utils.selftest import risk_summary, run_selftest
from utils.settings import get_settings
from utils.workers import JobWorker


class _NavItem(QWidget):
    """紧凑侧栏项：左侧钉子置顶按钮 + 页面名。"""

    ROW_HEIGHT = 26

    def __init__(self, index: int, title: str, pinned: bool,
                 on_show, on_toggle_pin):
        super().__init__()
        self.index = index
        self.title = title
        self.pinned = pinned
        self.setFixedHeight(self.ROW_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 0, 6, 0)
        layout.setSpacing(2)

        self.pin_btn = QToolButton()
        self.pin_btn.setObjectName("SidebarPinButton")
        self.pin_btn.setAutoRaise(True)
        self.pin_btn.setFixedSize(18, 22)
        self.pin_btn.setIconSize(QSize(12, 12))
        self.pin_btn.setToolTip("置顶" if not pinned else "取消置顶")
        self.pin_btn.clicked.connect(
            lambda _=False: on_toggle_pin(self.index))
        self.set_pin_state(pinned)

        self.label_btn = PushButton(title)
        self.label_btn.setObjectName("SidebarNavButton")
        self.label_btn.setFixedHeight(22)
        self.label_btn.clicked.connect(lambda _=False: on_show(self.index))

        layout.addWidget(self.pin_btn)
        layout.addWidget(self.label_btn, stretch=1)

    def set_active(self, active: bool):
        self.label_btn.setProperty("active", active)
        self.label_btn.style().unpolish(self.label_btn)
        self.label_btn.style().polish(self.label_btn)

    def set_pin_state(self, pinned: bool):
        self.pinned = pinned
        self.pin_btn.setIcon(
            (FluentIcon.PIN if pinned else FluentIcon.UNPIN).icon())
        self.pin_btn.setToolTip("取消置顶" if pinned else "置顶")

    def apply_metrics(self, font_size: int, padding_v: int):
        label_h = font_size + padding_v * 2 + 6
        self.label_btn.setFixedHeight(label_h)
        self.pin_btn.setFixedHeight(label_h)
        self.setFixedHeight(label_h + 2)


class MainWindow(QWidget):
    PIN_LIMIT = 5

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 工具")
        self.resize(940, 620)
        self._nav_items: list[_NavItem] = []
        self._pinned_order: list[int] = []
        self._animating = False
        self._slide_group = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.sidebar = self._build_sidebar()
        root.addWidget(self.sidebar)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, stretch=1)

        pages = pdf_tool_pages() + custom_pdf_pages() + doc_conversion_pages()
        self.pages = pages
        for page in pages:
            self.stack.addWidget(page)
        self._build_nav(pages)
        self._apply_sidebar_settings()

        self._selftest_page = SelfTestPage()
        self._selftest_index = self.stack.addWidget(self._selftest_page)
        self._auto_selftest_if_enabled()

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet(self._sidebar_style())
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(1)

        title = SubtitleLabel("PDF 工具")
        title.setStyleSheet("color:#1f2937;font-weight:bold;font-size:16px;")
        layout.addWidget(title)

        section = QLabel("工具")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)

        self.nav_scroll = QScrollArea()
        self.nav_scroll.setWidgetResizable(True)
        self.nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav_scroll.setFrameShape(QFrame.NoFrame)
        self.nav_scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollBar:vertical{width:5px;background:transparent;}"
            "QScrollBar::handle:vertical{background:#cbd5e1;border-radius:2px;}")
        nav_host = QWidget()
        self.nav_box = QVBoxLayout(nav_host)
        self.nav_box.setContentsMargins(0, 0, 0, 0)
        self.nav_box.setSpacing(0)
        self.nav_scroll.setWidget(nav_host)
        layout.addWidget(self.nav_scroll, stretch=1)

        settings_btn = PushButton("设置")
        selftest_btn = PushButton("自测")
        self.action_buttons = (settings_btn, selftest_btn)
        for btn in (settings_btn, selftest_btn):
            btn.setObjectName("SidebarActionButton")
            btn.setFixedHeight(22)
        settings_btn.clicked.connect(self._open_settings)
        selftest_btn.clicked.connect(self._show_selftest)
        layout.addWidget(settings_btn)
        layout.addWidget(selftest_btn)
        return sidebar

    def _build_nav(self, pages):
        self._pinned_order = list(range(min(self.PIN_LIMIT, len(pages))))
        for index, page in enumerate(pages):
            item = _NavItem(
                index, page.title, index in self._pinned_order,
                self._show_page, self._toggle_pin)
            self._nav_items.append(item)
        self._render_nav()
        self._show_page(0)

    def _toggle_pin(self, index: int):
        if index in self._pinned_order:
            self._pinned_order.remove(index)
        else:
            evicted = None
            if len(self._pinned_order) >= self.PIN_LIMIT:
                evicted = self._pinned_order.pop()
            self._pinned_order.insert(0, index)
            if evicted is not None:
                toast(self, "置顶数量已达上限",
                      f"已自动取消最早置顶项：{self._nav_items[evicted].title}",
                      "warning")
        for item in self._nav_items:
            item.set_pin_state(item.index in self._pinned_order)
        self._render_nav()

    def _render_nav(self):
        while self.nav_box.count():
            item = self.nav_box.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        pinned = set(self._pinned_order)
        for index in self._pinned_order:
            if 0 <= index < len(self._nav_items):
                self.nav_box.addWidget(self._nav_items[index])
                self._nav_items[index].show()
        for item in self._nav_items:
            if item.index not in pinned:
                self.nav_box.addWidget(item)
                item.show()

    def _show_page(self, index: int):
        self._slide_to(index)
        for item in self._nav_items:
            item.set_active(item.index == index)

    def _show_selftest(self):
        self._slide_to(self._selftest_index)
        for item in self._nav_items:
            item.set_active(False)

    def _slide_to(self, index: int):
        current = self.stack.currentIndex()
        if index == current:
            return
        if self._animating:
            return
        if not self.isVisible() or self.stack.width() < 5:
            self.stack.setCurrentIndex(index)
            return

        old_widget = self.stack.currentWidget()
        self.stack.setCurrentIndex(index)
        new_widget = self.stack.currentWidget()
        old_pix = old_widget.grab()
        new_pix = new_widget.grab()
        self.stack.setCurrentIndex(current)

        width = max(1, self.stack.width())
        height = max(1, self.stack.height())
        overlay = QWidget(self.stack)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay.setGeometry(0, 0, width, height)
        old_label = QLabel(overlay)
        old_label.setPixmap(old_pix)
        old_label.setGeometry(0, 0, width, height)
        new_label = QLabel(overlay)
        new_label.setPixmap(new_pix)
        new_label.setGeometry(0, 0, width, height)

        direction = 1 if index > current else -1
        new_label.move(direction * width, 0)
        overlay.show()
        overlay.raise_()

        self._animating = True
        group = QParallelAnimationGroup(self)
        old_anim = QPropertyAnimation(old_label, b"pos", group)
        old_anim.setDuration(180)
        old_anim.setStartValue(old_label.pos())
        old_anim.setEndValue(QPoint(
            old_label.pos().x() - direction * width,
            old_label.pos().y()))
        old_anim.setEasingCurve(QEasingCurve.OutCubic)

        new_anim = QPropertyAnimation(new_label, b"pos", group)
        new_anim.setDuration(180)
        new_anim.setStartValue(new_label.pos())
        new_anim.setEndValue(QPoint(0, 0))
        new_anim.setEasingCurve(QEasingCurve.OutCubic)
        group.addAnimation(old_anim)
        group.addAnimation(new_anim)
        group.finished.connect(lambda: self._finish_slide(index, overlay))
        self._slide_group = group
        group.start()

    def _finish_slide(self, index: int, overlay: QWidget):
        self.stack.setCurrentIndex(index)
        overlay.deleteLater()
        self._animating = False
        self._slide_group = None

    def _sidebar_style(self):
        cfg = get_settings()
        font = int(cfg.get("nav_font_size", 11) or 11)
        pad_h = int(cfg.get("nav_padding_h", 6) or 6)
        pad_v = int(cfg.get("nav_padding_v", 3) or 3)
        return (
            "#Sidebar{background:transparent;border:none;}"
            "#SidebarPinButton{background:transparent;border:none;padding:0;}"
            "#SidebarPinButton:hover{background:#e2e8f0;}"
            "#SidebarNavButton{background:transparent;border:none;"
            f"font-size:{font}px;color:#1f2937;text-align:left;"
            f"padding:{pad_v}px {pad_h}px;"
            "border-radius:4px;}"
            "#SidebarNavButton:hover{background:#e2e8f0;}"
            "#SidebarNavButton[active=\"true\"]{background:#0ea5e9;"
            "color:#ffffff;}"
            "#SidebarActionButton{background:#e2e8f0;border:none;"
            "color:#1f2937;"
            f"font-size:{int(cfg.get('action_font_size', 10))}px;"
            "padding:4px 6px;"
            "border-radius:4px;}"
            "#SidebarActionButton:hover{background:#0ea5e9;color:#ffffff;}"
            "#SectionTitle{color:#64748b;font-size:11px;padding:2px 4px;}"
        )

    def _apply_sidebar_settings(self):
        cfg = get_settings()
        width = int(cfg.get("sidebar_width", 160) or 160)
        font = int(cfg.get("nav_font_size", 11) or 11)
        pad_v = int(cfg.get("nav_padding_v", 3) or 3)
        action_font = int(cfg.get("action_font_size", 10) or 10)
        action_height = int(cfg.get("action_height", 22) or 22)
        window_w = int(cfg.get("window_width", 940) or 940)
        window_h = int(cfg.get("window_height", 620) or 620)
        margin = int(cfg.get("content_margin", 16) or 16)
        spacing = int(cfg.get("content_spacing", 6) or 6)
        log_h = int(cfg.get("log_height", 92) or 92)
        self.sidebar.setFixedWidth(width)
        self.sidebar.setStyleSheet(self._sidebar_style())
        self.resize(window_w, window_h)
        for btn in self.action_buttons:
            btn.setFixedHeight(action_height)
        for btn in self.action_buttons:
            btn.setFont(self._font(action_font))
        for item in self._nav_items:
            item.apply_metrics(font, pad_v)
        for page in getattr(self, "pages", []):
            if hasattr(page, "apply_page_layout"):
                try:
                    page.apply_page_layout(
                        margin, spacing, log_height=log_h)
                except TypeError:
                    page.apply_page_layout(margin, spacing)
        if hasattr(self, "_selftest_page"):
            self._selftest_page.apply_page_layout(margin, spacing)

    @staticmethod
    def _font(size):
        from PySide6.QtGui import QFont
        return QFont("Microsoft YaHei UI", size)

    def _open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            self._apply_sidebar_settings()

    def _auto_selftest_if_enabled(self):
        if not get_settings().get("auto_selftest_on_startup", True):
            return
        QTimer.singleShot(500, self._run_auto_selftest)

    def _run_auto_selftest(self):
        worker = JobWorker(lambda progress: run_selftest(progress), self)
        worker.succeeded.connect(self._auto_selftest_done)
        worker.failed.connect(
            lambda msg: toast(self, "自测失败", str(msg), "error"))
        worker.start()

    def _auto_selftest_done(self, results):
        summary = risk_summary(results)
        get_logger().info("启动自测：%s", summary)
        if summary.startswith("未发现"):
            toast(self, "自测完成", summary, "success")
        else:
            toast(self, "自测完成", summary, "warning")
