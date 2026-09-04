# -*- coding: utf-8 -*-
"""基础 PDF 工具页：通过统一参数表单 + service 接口组装。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import QCheckBox, QComboBox, QDoubleSpinBox, QLineEdit
from PySide6.QtWidgets import QPlainTextEdit, QPushButton, QSpinBox, QWidget
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QVBoxLayout
from qfluentwidgets import CheckBox

from services import (content_service, document_service, overlay_service,
                      pdf_service)
from utils.files import IMAGE_EXTS, OFFICE_EXTS
from ui.common.tool_page import ToolPage


class _FileParamWidget(QWidget):
    """带浏览按钮的路径输入控件。"""

    def __init__(self, file_type: str = "图片"):
        super().__init__()
        self._file_type = file_type
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.line_edit = QLineEdit()
        self.browse_btn = QPushButton("浏览")
        layout.addWidget(self.line_edit)
        layout.addWidget(self.browse_btn)
        self.browse_btn.clicked.connect(self._browse)

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, f"选择{self._file_type}")
        if path:
            self.line_edit.setText(path)


class _TextAreaParamWidget(QWidget):
    """多行文本参数输入。"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.edit = QPlainTextEdit()
        self.edit.setMaximumHeight(100)
        layout.addWidget(self.edit)

    def to_text(self):
        return self.edit.toPlainText()


@dataclass
class ParamSpec:
    key: str
    label: str
    kind: str  # combo / check / spin / double / text / file_path / textarea
    values: tuple = ()
    default_value: object = None
    minimum: int | float = 0
    maximum: int | float = 9999


@dataclass
class ToolSpec:
    title: str
    description: str
    job: Callable[[list[str], str, dict, Callable[[str], None]], str]
    params: tuple = ()
    exts: tuple = (".pdf",)
    output_kind: str = "file"
    single_mode: bool = True
    object_name: str = ""


def build_page(spec: ToolSpec) -> ToolPage:
    """根据 ToolSpec 动态生成统一风格的工具页。"""

    class GeneratedPage(ToolPage):
        def __init__(self):
            super().__init__(
                spec.title, spec.description, exts=spec.exts,
                output_kind=spec.output_kind,
                object_name=spec.object_name or spec.title,
                single_mode=spec.single_mode)
            self._controls: dict = {}
            for param in spec.params:
                widget = self._create_widget(param)
                self._controls[param.key] = widget
                self.add_row(param.label, widget)

        @staticmethod
        def _create_widget(param: ParamSpec):
            if param.kind == "combo":
                combo = QComboBox()
                combo.addItems(param.values)
                if param.default_value:
                    combo.setCurrentText(param.default_value)
                return combo
            if param.kind == "check":
                box = CheckBox()
                box.setChecked(bool(param.default_value))
                return box
            if param.kind == "spin":
                spin = QSpinBox()
                spin.setRange(int(param.minimum), int(param.maximum))
                spin.setValue(int(param.default_value or 0))
                return spin
            if param.kind == "double":
                spin = QDoubleSpinBox()
                spin.setRange(float(param.minimum), float(param.maximum))
                spin.setDecimals(1)
                spin.setValue(float(param.default_value or 0))
                return spin
            if param.kind == "text":
                edit = QLineEdit()
                if param.default_value:
                    edit.setText(str(param.default_value))
                return edit
            if param.kind == "file_path":
                widget = _FileParamWidget(
                    str(param.default_value or "文件"))
                return widget
            if param.kind == "textarea":
                return _TextAreaParamWidget()
            raise ValueError(f"未知参数类型：{param.kind}")

        def _value(self, param: ParamSpec):
            widget = self._controls[param.key]
            if isinstance(widget, QComboBox):
                return widget.currentText()
            if isinstance(widget, QCheckBox):
                return widget.isChecked()
            if isinstance(widget, QSpinBox):
                return widget.value()
            if isinstance(widget, QDoubleSpinBox):
                return widget.value()
            if isinstance(widget, _FileParamWidget):
                return widget.line_edit.text().strip()
            if isinstance(widget, _TextAreaParamWidget):
                return widget.to_text()
            return widget.text().strip()

        def make_job(self, paths, output):
            values = {p.key: self._value(p) for p in spec.params}

            def job(progress):
                return spec.job(paths, output, values, progress)

            return job

    return GeneratedPage()


def _run_each_dir(func, paths, outdir, values, progress):
    for i, src in enumerate(paths, start=1):
        progress(f"正在处理 {i}/{len(paths)}：{src}")
        func(src, outdir, **values, progress=progress)
    return f"已处理 {len(paths)} 个文件，输出位置：{outdir}"


def _merge_job(paths, output, values, progress):
    return pdf_service.merge_pdfs(paths, output, progress)


def _split_job(paths, outdir, values, progress):
    mode = "all" if values["mode"] == "全部页面" else "range"
    for i, src in enumerate(paths, start=1):
        progress(f"正在处理 {i}/{len(paths)}：{src}")
        pdf_service.split_pdf(
            src, outdir, mode=mode,
            from_page=int(values["from_page"]), to_page=int(values["to_page"]),
            progress=progress)
    return f"拆分完成，输出位置：{outdir}"


def _compress_job(paths, output, values, progress):
    src = paths[0]
    return pdf_service.compress_pdf(
        src, output,
        compress_streams=bool(values["compress_streams"]),
        remove_duplicates=bool(values["remove_duplicates"]),
        strip_metadata=bool(values["strip_metadata"]),
        progress=progress)


def _rotate_job(paths, output, values, progress):
    src = paths[0]
    mode = {"全部页面": "all", "指定页码范围": "range",
            "指定页码": "specific"}.get(values["mode"], "all")
    angle_map = {"顺时针 90°": 90, "180°": 180, "逆时针 90°": 270}
    return pdf_service.rotate_pdf(
        src, output, angle=angle_map.get(values["angle"], 90), mode=mode,
        from_page=int(values["from_page"]), to_page=int(values["to_page"]),
        specific=values.get("specific", ""), progress=progress)


def _crop_job(paths, output, values, progress):
    src = paths[0]
    mode = "all" if values["mode"] == "全部页面" else "range"
    return pdf_service.crop_pdf(
        src, output, top=float(values["top"]), bottom=float(values["bottom"]),
        left=float(values["left"]), right=float(values["right"]),
        mode=mode, from_page=int(values["from_page"]),
        to_page=int(values["to_page"]), progress=progress)


def _blank_job(paths, output, values, progress):
    src = paths[0]
    return pdf_service.remove_blank_pages(
        src, output, threshold=int(values["threshold"]), progress=progress)


def _repair_job(paths, output, values, progress):
    src = paths[0]
    return pdf_service.repair_pdf(
        src, output, strict=bool(values["strict"]),
        copy_metadata=bool(values["copy_metadata"]), progress=progress)


def _password_job(paths, output, values, progress):
    src = paths[0]
    if values["action"] == "移除密码":
        return pdf_service.remove_pdf_password(
            src, output, password=values.get("password", ""),
            progress=progress)
    return pdf_service.protect_pdf(
        src, output, user_password=values.get("password", ""),
        owner_password=values.get("owner_password", "") or None,
        algorithm=values.get("algorithm", "AES-256"), progress=progress)


def _metadata_job(paths, output, values, progress):
    src = paths[0]
    fields = {}
    for key, _label in pdf_service.METADATA_FIELDS:
        fields[key] = values.get(key, "")
    return pdf_service.save_metadata(src, output, fields, progress)


def _watermark_job(paths, output, values, progress):
    src = paths[0]
    mode = "image" if values["mode"] == "图片水印" else "text"
    return overlay_service.watermark_pdf(
        src, output, mode=mode, text=values.get("text", "CONFIDENTIAL"),
        font_size=int(values["font_size"]), color_key=values["color"],
        angle=int(values["angle"]), opacity=int(values["opacity"]),
        image_path=values.get("image", ""),
        scale_pct=int(values.get("scale", 50)), progress=progress)


def _page_number_job(paths, output, values, progress):
    src = paths[0]
    return overlay_service.add_page_numbers(
        src, output, position=values["position"], fmt=values["format"],
        start=int(values["start"]), font_size=int(values["font_size"]),
        color_key=values["color"], margin_mm=float(values["margin"]),
        skip_first=bool(values["skip_first"]), progress=progress)


def _nup_job(paths, output, values, progress):
    src = paths[0]
    return overlay_service.nup_pdf(
        src, output, layout_key=values["layout"], size_key=values["size"],
        order_key=values["order"], gap_mm=float(values["gap"]),
        margin_mm=float(values["margin"]),
        draw_border=bool(values["border"]), progress=progress)


def _extract_text_job(paths, outdir, values, progress):
    src = paths[0]
    results = []
    mode = values.get("mode", "全部页面")
    mode = "all" if mode == "全部页面" else "range"
    if values.get("txt"):
        results.append(content_service.export_text_txt(
            src, outdir, mode=mode,
            from_page=int(values.get("from_page", 1)),
            to_page=int(values.get("to_page", 1)), progress=progress))
    if values.get("docx"):
        results.append(content_service.export_text_docx(
            src, outdir, mode=mode,
            from_page=int(values.get("from_page", 1)),
            to_page=int(values.get("to_page", 1)), progress=progress))
    if not results:
        raise ValueError("请至少选择 TXT 或 DOCX")
    return "；".join(results)


def _extract_images_job(paths, outdir, values, progress):
    src = paths[0]
    mode = values.get("mode", "全部页面")
    mode = "all" if mode == "全部页面" else "range"
    formats = tuple(k for k in ("PNG", "JPG", "TIFF", "WebP")
                    if values.get(k))
    if not formats:
        raise ValueError("请至少选择一种图片格式")
    return content_service.extract_images(
        src, outdir, formats=formats, quality=int(values["quality"]),
        mode=mode, from_page=int(values.get("from_page", 1)),
        to_page=int(values.get("to_page", 1)), progress=progress)


def _signature_job(paths, output, values, progress):
    src = paths[0]
    if not values.get("image"):
        raise ValueError("请先选择签名图片")
    scope = {"最后一页": "last", "全部页面": "all",
             "指定页码": "specific"}.get(values["scope"], "last")
    return overlay_service.apply_signature(
        src, output, image_path=values["image"],
        position=values["position"], width_mm=float(values["width"]),
        margin_mm=float(values["margin"]), opacity=int(values["opacity"]),
        scope=scope, pages_text=values.get("pages", ""),
        progress=progress)


def _ocr_job(paths, output, values, progress):
    return content_service.ocr_pdf(
        paths[0], output, lang=values["lang"], dpi=int(values["dpi"]),
        progress=progress)


def _compare_job(paths, outdir, values, progress):
    if len(paths) < 2:
        raise ValueError("请添加两个 PDF：先原版，后修改版")
    result = content_service.compare_pdfs(
        paths[0], paths[1], progress)
    outdir = os.path.join(os.path.abspath(outdir), "")
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "对比结果.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(result)
    progress(result)
    return f"对比结果已保存：{os.path.basename(out)}"


def _info_job(paths, outdir, values, progress):
    result = content_service.pdf_info(paths[0])
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, "PDF信息.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(result)
    progress(result)
    return f"PDF 信息已保存：{os.path.basename(out)}"


def _image_to_pdf_job(paths, output, values, progress):
    return document_service.images_to_pdf(
        paths, output, values["size"], progress)


def _office_to_pdf_job(paths, outdir, values, progress):
    return document_service.office_to_pdf_batch(paths, outdir, progress)


def merge_page():
    return build_page(ToolSpec(
        title="合并 PDF", description="将多个 PDF 按列表顺序合并为一个文件。",
        job=_merge_job, single_mode=False,
        object_name="merge_pdf"))


def split_page():
    return build_page(ToolSpec(
        title="拆分 PDF",
        description="将 PDF 逐页保存，或提取指定页码范围。",
        job=_split_job,
        output_kind="dir",
        params=(
            ParamSpec("mode", "拆分模式", "combo",
                      ("全部页面", "指定页码范围"), "全部页面"),
            ParamSpec("from_page", "起始页", "spin", default_value=1,
                      minimum=1),
            ParamSpec("to_page", "结束页", "spin", default_value=1,
                      minimum=1),
        ),
        object_name="split_pdf"))


def compress_page():
    return build_page(ToolSpec(
        title="压缩 PDF", description="压缩数据流、删除重复对象并降低文件体积。",
        job=_compress_job,
        params=(
            ParamSpec("compress_streams", "压缩内容数据流", "check",
                      default_value=True),
            ParamSpec("remove_duplicates", "删除重复对象", "check",
                      default_value=True),
            ParamSpec("strip_metadata", "移除元数据", "check",
                      default_value=False),
        ),
        object_name="compress_pdf"))


def rotate_page():
    return build_page(ToolSpec(
        title="旋转页面", description="按 90°、180°、270° 旋转 PDF 页面。",
        job=_rotate_job,
        params=(
            ParamSpec("mode", "处理范围", "combo",
                      ("全部页面", "指定页码范围", "指定页码"), "全部页面"),
            ParamSpec("from_page", "起始页", "spin", default_value=1, minimum=1),
            ParamSpec("to_page", "结束页", "spin", default_value=1, minimum=1),
            ParamSpec("specific", "指定页码，如 1,3,5-8", "text",
                      default_value=""),
            ParamSpec("angle", "旋转角度", "combo",
                      ("顺时针 90°", "180°", "逆时针 90°"), "顺时针 90°"),
        ),
        object_name="rotate_pdf"))


def crop_page():
    return build_page(ToolSpec(
        title="裁剪页边距",
        description="按毫米裁剪 PDF 页面四周边距。",
        job=_crop_job,
        params=(
            ParamSpec("mode", "处理范围", "combo",
                      ("全部页面", "指定页码范围"), "全部页面"),
            ParamSpec("from_page", "起始页", "spin", default_value=1,
                      minimum=1),
            ParamSpec("to_page", "结束页", "spin", default_value=1,
                      minimum=1),
            ParamSpec("top", "上边距（mm）", "double", default_value=0),
            ParamSpec("bottom", "下边距（mm）", "double", default_value=0),
            ParamSpec("left", "左边距（mm）", "double", default_value=0),
            ParamSpec("right", "右边距（mm）", "double", default_value=0),
        ),
        object_name="crop_pdf"))


def remove_blanks_page():
    return build_page(ToolSpec(
        title="删除空白页",
        description="删除字符数低于阈值的近似空白页面。",
        job=_blank_job,
        params=(
            ParamSpec("threshold", "空白阈值（字符数）", "spin",
                      default_value=100, minimum=1, maximum=2000),
        ),
        object_name="remove_blanks"))


def repair_page():
    return build_page(ToolSpec(
        title="修复 PDF",
        description="逐页重建损坏 PDF，尽量恢复可读页面。",
        job=_repair_job,
        params=(
            ParamSpec("strict", "严格模式（遇到坏页即停止）", "check",
                      default_value=False),
            ParamSpec("copy_metadata", "复制原始元数据", "check",
                      default_value=True),
        ),
        object_name="repair_pdf"))


def password_page():
    return build_page(ToolSpec(
        title="密码保护",
        description="为 PDF 添加密码，或使用正确密码移除加密。",
        job=_password_job,
        params=(
            ParamSpec("action", "操作", "combo",
                      ("设置密码", "移除密码"), "设置密码"),
            ParamSpec("password", "打开密码 / 当前密码", "text"),
            ParamSpec("owner_password", "所有者密码（可选）", "text"),
            ParamSpec("algorithm", "加密算法", "combo",
                      ("AES-256", "AES-128"), "AES-256"),
        ),
        object_name="password_pdf"))


def metadata_page():
    specs = [
        ParamSpec(key, label, "text")
        for key, label in pdf_service.METADATA_FIELDS
    ]
    return build_page(ToolSpec(
        title="元数据",
        description="查看并编辑 PDF 标题、作者、主题等元数据。",
        job=_metadata_job,
        params=tuple(specs),
        object_name="metadata_pdf"))


def watermark_page():
    return build_page(ToolSpec(
        title="添加水印",
        description="为每一页添加文字水印，可设置字号、颜色、角度与透明度。",
        job=_watermark_job,
        params=(
            ParamSpec("mode", "水印类型", "combo",
                      ("文字水印", "图片水印"), "文字水印"),
            ParamSpec("text", "水印文字", "text",
                      default_value="CONFIDENTIAL"),
            ParamSpec("image", "水印图片", "file_path",
                      default_value="水印图片"),
            ParamSpec("font_size", "字号", "spin", default_value=60,
                      minimum=8, maximum=200),
            ParamSpec("color", "颜色", "combo",
                      ("灰色", "黑色", "白色", "红色", "蓝色"), "灰色"),
            ParamSpec("angle", "角度", "combo",
                      ("45", "0", "90"), "45"),
            ParamSpec("scale", "图片缩放（%页面宽）", "spin",
                      default_value=50, minimum=5, maximum=100),
            ParamSpec("opacity", "不透明度（%）", "spin",
                      default_value=30, minimum=5, maximum=100),
        ),
        object_name="watermark_pdf"))


def page_numbers_page():
    return build_page(ToolSpec(
        title="添加页码",
        description="按位置、格式、颜色为 PDF 添加页码。",
        job=_page_number_job,
        params=(
            ParamSpec("position", "位置", "combo",
                      ("底部居中", "底部靠左", "底部靠右",
                       "顶部居中", "顶部靠左", "顶部靠右"), "底部居中"),
            ParamSpec("format", "格式", "combo",
                      ("1", "第 1 页", "1 / {total}",
                       "第 1 页，共 {total} 页", "- 1 -"), "1 / {total}"),
            ParamSpec("start", "起始页码", "spin", default_value=1,
                      minimum=0),
            ParamSpec("font_size", "字号", "spin", default_value=10,
                      minimum=6, maximum=72),
            ParamSpec("color", "颜色", "combo",
                      ("黑色", "灰色", "白色"), "黑色"),
            ParamSpec("margin", "边距（mm）", "double", default_value=10,
                      maximum=50),
            ParamSpec("skip_first", "跳过第一页（封面）", "check",
                      default_value=False),
        ),
        object_name="page_numbers"))


def nup_page():
    return build_page(ToolSpec(
        title="N 合 1",
        description="将多个 PDF 页面拼版到一张纸上。",
        job=_nup_job,
        params=(
            ParamSpec("layout", "拼版方式", "combo",
                      ("2 合 1（1×2 横向）", "4 合 1（2×2）",
                       "6 合 1（2×3 横向）", "9 合 1（3×3）"),
                      "2 合 1（1×2 横向）"),
            ParamSpec("size", "输出纸张", "combo",
                      ("A4 纵向（210×297 mm）", "A4 横向（297×210 mm）",
                       "Letter 纵向（8.5×11\"）",
                       "Letter 横向（11×8.5\"）"),
                      "A4 横向（297×210 mm）"),
            ParamSpec("order", "页面顺序", "combo",
                      ("从左到右", "从上到下"), "从左到右"),
            ParamSpec("gap", "单元格间距（mm）", "double", default_value=4,
                      maximum=30),
            ParamSpec("margin", "外页边距（mm）", "double", default_value=6,
                      maximum=50),
            ParamSpec("border", "绘制单元格边框", "check",
                      default_value=False),
        ),
        object_name="nup_pdf"))


def extract_text_page():
    return build_page(ToolSpec(
        title="提取文本",
        description="从 PDF 提取文本，导出 TXT 或 DOCX。",
        job=_extract_text_job,
        output_kind="dir",
        params=(
            ParamSpec("mode", "处理范围", "combo",
                      ("全部页面", "指定页码范围"), "全部页面"),
            ParamSpec("from_page", "起始页", "spin", default_value=1,
                      minimum=1),
            ParamSpec("to_page", "结束页", "spin", default_value=1,
                      minimum=1),
            ParamSpec("txt", "导出 TXT", "check", default_value=True),
            ParamSpec("docx", "导出 DOCX（Word）", "check",
                      default_value=True),
        ),
        object_name="extract_text"))


def extract_images_page():
    return build_page(ToolSpec(
        title="提取图片",
        description="导出 PDF 中内嵌的图片，可多格式同时输出。",
        job=_extract_images_job,
        output_kind="dir",
        params=(
            ParamSpec("mode", "处理范围", "combo",
                      ("全部页面", "指定页码范围"), "全部页面"),
            ParamSpec("from_page", "起始页", "spin", default_value=1,
                      minimum=1),
            ParamSpec("to_page", "结束页", "spin", default_value=1,
                      minimum=1),
            ParamSpec("PNG", "PNG", "check", default_value=True),
            ParamSpec("JPG", "JPG", "check", default_value=True),
            ParamSpec("TIFF", "TIFF", "check", default_value=False),
            ParamSpec("WebP", "WebP", "check", default_value=False),
            ParamSpec("quality", "JPG/WebP 质量", "spin",
                      default_value=85, minimum=10, maximum=100),
        ),
        object_name="extract_images"))


def signature_page():
    return build_page(ToolSpec(
        title="添加签名",
        description="在指定页面放置签名图片。",
        job=_signature_job,
        params=(
            ParamSpec("image", "签名图片", "file_path",
                      default_value="签名图片"),
            ParamSpec("position", "位置", "combo",
                      ("底部靠右", "底部靠左", "底部居中",
                       "顶部靠右", "顶部靠左", "顶部居中"), "底部靠右"),
            ParamSpec("width", "宽度（mm）", "double", default_value=40,
                      maximum=200),
            ParamSpec("margin", "边距（mm）", "double", default_value=10,
                      maximum=100),
            ParamSpec("opacity", "不透明度（%）", "spin",
                      default_value=100, minimum=10, maximum=100),
            ParamSpec("scope", "应用到", "combo",
                      ("最后一页", "全部页面", "指定页码"), "最后一页"),
            ParamSpec("pages", "指定页码，如 1,3,5-8", "text"),
        ),
        object_name="signature_pdf"))


def ocr_page():
    return build_page(ToolSpec(
        title="OCR 识别",
        description="使用 Tesseract 将扫描版 PDF 转为可搜索 PDF。",
        job=_ocr_job,
        params=(
            ParamSpec("lang", "语言代码", "combo",
                      ("chi_sim", "eng", "deu", "fra", "rus", "spa"),
                      "chi_sim"),
            ParamSpec("dpi", "渲染 DPI", "spin", default_value=300,
                      minimum=72, maximum=600),
        ),
        object_name="ocr_pdf"))


def compare_page():
    return build_page(ToolSpec(
        title="比较 PDF",
        description="按顺序添加两个 PDF：原版在前，修改版在后，输出文本差异。",
        job=_compare_job,
        output_kind="dir",
        single_mode=False,
        object_name="compare_pdfs"))


def info_page():
    return build_page(ToolSpec(
        title="PDF 信息",
        description="查看 PDF 的页数与元数据。",
        job=_info_job,
        output_kind="dir",
        object_name="pdf_info"))


def image_to_pdf_page():
    return build_page(ToolSpec(
        title="图片转 PDF",
        description="将多张图片按顺序合并为 PDF。",
        job=_image_to_pdf_job,
        exts=IMAGE_EXTS,
        single_mode=False,
        params=(
            ParamSpec("size", "页面尺寸", "combo",
                      ("原始尺寸", "A4 纵向", "A4 横向",
                       "Letter 纵向", "Letter 横向"), "原始尺寸"),
        ),
        object_name="images_to_pdf"))


def office_to_pdf_page():
    return build_page(ToolSpec(
        title="Office 转 PDF",
        description="使用 LibreOffice 将 Word、Excel、PPT 转 PDF。",
        job=_office_to_pdf_job,
        exts=OFFICE_EXTS,
        output_kind="dir",
        single_mode=False,
        object_name="office_to_pdf"))


def pdf_tool_pages() -> list[ToolPage]:
    return [
        merge_page(), split_page(), compress_page(), rotate_page(),
        crop_page(), remove_blanks_page(), repair_page(), password_page(),
        watermark_page(), page_numbers_page(), nup_page(),
        extract_text_page(), extract_images_page(),
        signature_page(), ocr_page(), compare_page(), info_page(),
        image_to_pdf_page(), office_to_pdf_page(),
    ]
