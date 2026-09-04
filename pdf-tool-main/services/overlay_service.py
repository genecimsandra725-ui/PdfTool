# -*- coding: utf-8 -*-
"""叠加渲染服务：水印、页码、签名、遮盖、N 合 1。"""

from __future__ import annotations

import io
import math
import os
from collections.abc import Callable

from utils.errors import AppError
from utils.files import ensure_pdf_suffix

ProgressFn = Callable[[str], None]
_NOOP: ProgressFn = lambda msg: None


def _open_reader(src: str):
    from pypdf import PdfReader
    if not os.path.isfile(src):
        raise AppError(f"文件不存在：{src}")
    try:
        reader = PdfReader(src)
    except Exception as exc:
        raise AppError(f"无法打开 PDF：{os.path.basename(src)}（{exc}）") from exc
    if reader.is_encrypted:
        raise AppError(f"PDF“{os.path.basename(src)}”已加密，请先移除密码")
    return reader


def _writer():
    from pypdf import PdfWriter
    return PdfWriter()


def _save(writer, output: str):
    with open(output, "wb") as fh:
        writer.write(fh)


def _overlay_bytes(width: float, height: float, painter) -> object:
    """painter(canvas, width, height) 在 reportlab 画布上绘制叠加层。"""
    from pypdf import PdfReader
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    painter(c, width, height)
    c.save()
    buf.seek(0)
    return PdfReader(buf).pages[0]


def watermark_pdf(
    src: str,
    output: str,
    mode: str = "text",
    text: str = "CONFIDENTIAL",
    font_size: int = 60,
    color_key: str = "灰色",
    angle: int = 45,
    image_path: str = "",
    scale_pct: int = 50,
    opacity: int = 30,
    progress: ProgressFn = _NOOP,
) -> str:
    """给 PDF 每一页叠加文字或图片水印。"""
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    writer = _writer()
    colors = {
        "灰色": (0.5, 0.5, 0.5), "黑色": (0.0, 0.0, 0.0),
        "白色": (1.0, 1.0, 1.0), "红色": (0.8, 0.1, 0.1),
        "蓝色": (0.1, 0.3, 0.8),
    }
    rgb = colors.get(color_key, colors["灰色"])
    total = len(reader.pages)

    for index, page in enumerate(reader.pages, start=1):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        alpha = opacity / 100

        if mode == "text":
            def paint(c, pw, ph):
                from reportlab.lib.colors import Color
                c.saveState()
                c.setFillColor(Color(*rgb, alpha=alpha))
                c.setFont("Helvetica-Bold", float(font_size))
                c.translate(pw / 2, ph / 2)
                c.rotate(float(angle))
                c.drawCentredString(0, 0, text)
                c.restoreState()
        else:
            if not image_path or not os.path.isfile(image_path):
                raise AppError("请选择有效的水印图片")
            from PIL import Image
            with Image.open(image_path) as img:
                iw, ih = img.size
            draw_w = w * scale_pct / 100
            draw_h = ih * draw_w / max(1, iw)
            x = (w - draw_w) / 2
            y = (h - draw_h) / 2

            def paint(c, pw, ph):
                c.saveState()
                c.setFillAlpha(alpha)
                c.drawImage(image_path, x, y, width=draw_w,
                            height=draw_h, mask="auto")
                c.restoreState()

        overlay = _overlay_bytes(w, h, paint)
        page.merge_page(overlay)
        writer.add_page(page)
        if index % 10 == 0 or index == total:
            progress(f"水印处理中：{index}/{total} 页")

    _save(writer, output)
    return f"已为 {total} 页添加水印，输出：{os.path.basename(output)}"


def add_page_numbers(
    src: str,
    output: str,
    position: str = "底部居中",
    fmt: str = "1 / {total}",
    start: int = 1,
    font_size: int = 10,
    color_key: str = "黑色",
    margin_mm: float = 10.0,
    skip_first: bool = False,
    progress: ProgressFn = _NOOP,
) -> str:
    """为 PDF 页面添加页码。"""
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    writer = _writer()
    mm = 2.8346
    positions = {
        "底部居中": "bc", "底部靠左": "bl", "底部靠右": "br",
        "顶部居中": "tc", "顶部靠左": "tl", "顶部靠右": "tr",
    }
    colors = {
        "黑色": (0, 0, 0), "灰色": (0.5, 0.5, 0.5),
        "白色": (1, 1, 1),
    }
    pos = positions.get(position, "bc")
    rgb = colors.get(color_key, colors["黑色"])
    total = len(reader.pages)
    margin_pt = margin_mm * mm

    for i, page in enumerate(reader.pages):
        if skip_first and i == 0:
            writer.add_page(page)
            continue
        display = start + i - (1 if skip_first else 0)
        label = fmt.replace("{total}", str(total))
        label = label.replace("1", str(display), 1)
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)

        def paint(c, pw, ph):
            from reportlab.lib.colors import Color
            c.setFillColor(Color(*rgb))
            c.setFont("Helvetica", float(font_size))
            m = margin_pt
            if pos == "bc":
                c.drawCentredString(pw / 2, m, label)
            elif pos == "bl":
                c.drawString(m, m, label)
            elif pos == "br":
                c.drawRightString(pw - m, m, label)
            elif pos == "tc":
                c.drawCentredString(pw / 2, ph - m - float(font_size), label)
            elif pos == "tl":
                c.drawString(m, ph - m - float(font_size), label)
            else:
                c.drawRightString(pw - m, ph - m - float(font_size), label)

        overlay = _overlay_bytes(w, h, paint)
        page.merge_page(overlay)
        writer.add_page(page)
        if (i + 1) % 10 == 0 or i + 1 == total:
            progress(f"页码处理中：{i + 1}/{total} 页")

    _save(writer, output)
    return f"已为 {total} 页添加页码，输出：{os.path.basename(output)}"


def apply_signature(
    src: str,
    output: str,
    image_path: str,
    position: str = "底部靠右",
    width_mm: float = 40.0,
    margin_mm: float = 10.0,
    opacity: int = 100,
    scope: str = "last",
    pages_text: str = "",
    progress: ProgressFn = _NOOP,
) -> str:
    """在指定页面放置签名图片。scope: last/all/specific。"""
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    writer = _writer()
    mm = 2.8346
    positions = {
        "底部靠右": "br", "底部靠左": "bl", "底部居中": "bc",
        "顶部靠右": "tr", "顶部靠左": "tl", "顶部居中": "tc",
    }
    pos = positions.get(position, "br")
    total = len(reader.pages)
    if scope == "all":
        pages = list(range(total))
    elif scope == "last":
        pages = [total - 1] if total else []
    else:
        pages = []
        for part in pages_text.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                pages.extend(range(int(a) - 1, min(int(b), total)))
            elif part.isdigit():
                pages.append(int(part) - 1)
    targets = set(pages)

    if not image_path or not os.path.isfile(image_path):
        raise AppError("请选择有效的签名图片")
    from PIL import Image
    with Image.open(image_path) as img:
        iw, ih = img.size
    w_pt = width_mm * mm
    h_pt = ih * w_pt / max(1, iw)
    m_pt = margin_mm * mm
    alpha = opacity / 100

    for i, page in enumerate(reader.pages):
        if i in targets:
            w = float(page.mediabox.width)
            h = float(page.mediabox.height)
            if pos == "br":
                x, y = w - w_pt - m_pt, m_pt
            elif pos == "bl":
                x, y = m_pt, m_pt
            elif pos == "bc":
                x, y = (w - w_pt) / 2, m_pt
            elif pos == "tr":
                x, y = w - w_pt - m_pt, h - h_pt - m_pt
            elif pos == "tl":
                x, y = m_pt, h - h_pt - m_pt
            else:
                x, y = (w - w_pt) / 2, h - h_pt - m_pt

            def paint(c, pw, ph):
                c.saveState()
                c.setFillAlpha(alpha)
                c.drawImage(image_path, x, y, width=w_pt, height=h_pt,
                            mask="auto")
                c.restoreState()

            page.merge_page(_overlay_bytes(w, h, paint))
        writer.add_page(page)
        progress(f"签名处理中：{i + 1}/{len(reader.pages)} 页")

    _save(writer, output)
    return f"签名已应用到 {len(targets)} 页，输出：{os.path.basename(output)}"


def apply_redaction(
    src: str,
    output: str,
    regions: list[tuple[int, float, float, float, float]],
    progress: ProgressFn = _NOOP,
) -> str:
    """遮盖敏感区域。regions: (1基页码, x_mm, y_mm, w_mm, h_mm)。"""
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    writer = _writer()
    mm = 2.8346
    if not regions:
        raise AppError("请至少添加一个遮盖区域")
    by_page: dict[int, list] = {}
    for page, x, y, w, h in regions:
        by_page.setdefault(page, []).append((x, y, w, h))

    for i, page in enumerate(reader.pages, start=1):
        page_regions = by_page.get(i, [])
        if page_regions:
            pw = float(page.mediabox.width)
            ph = float(page.mediabox.height)

            def paint(c, canvas_w, canvas_h):
                from reportlab.lib.colors import black
                c.setFillColor(black)
                for x_mm, y_mm, w_mm, h_mm in page_regions:
                    x_pt = x_mm * mm
                    w_pt = w_mm * mm
                    h_pt = h_mm * mm
                    y_pt = ph - (y_mm * mm) - h_pt
                    c.rect(x_pt, y_pt, w_pt, h_pt, fill=1, stroke=0)

            page.merge_page(_overlay_bytes(pw, ph, paint))
        writer.add_page(page)
        if i % 10 == 0 or i == len(reader.pages):
            progress(f"遮盖处理中：{i}/{len(reader.pages)} 页")

    _save(writer, output)
    return f"已遮盖 {len(regions)} 个区域，输出：{os.path.basename(output)}"


def nup_pdf(
    src: str,
    output: str,
    layout_key: str = "2 合 1（1×2 横向）",
    size_key: str = "A4 横向（297×210 mm）",
    order_key: str = "从左到右",
    gap_mm: float = 4.0,
    margin_mm: float = 6.0,
    draw_border: bool = False,
    progress: ProgressFn = _NOOP,
) -> str:
    """将 PDF 页面拼版到一张纸上。"""
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    from pypdf import PageObject, PdfReader, PdfWriter, Transformation

    layouts = {
        "2 合 1（1×2 横向）": (1, 2),
        "4 合 1（2×2）": (2, 2),
        "6 合 1（2×3 横向）": (2, 3),
        "9 合 1（3×3）": (3, 3),
    }
    sizes = {
        "A4 纵向（210×297 mm）": (595.28, 841.89),
        "A4 横向（297×210 mm）": (841.89, 595.28),
        "Letter 纵向（8.5×11\"）": (612.0, 792.0),
        "Letter 横向（11×8.5\"）": (792.0, 612.0),
    }
    rows, cols = layouts[layout_key]
    out_w, out_h = sizes[size_key]
    per_sheet = rows * cols
    mm = 2.8346
    gap = gap_mm * mm
    margin = margin_mm * mm
    avail_w = (out_w - 2 * margin - (cols - 1) * gap) / cols
    avail_h = (out_h - 2 * margin - (rows - 1) * gap) / rows
    writer = PdfWriter()
    pages = reader.pages
    total = len(pages)

    for sheet_start in range(0, total, per_sheet):
        chunk = pages[sheet_start:sheet_start + per_sheet]
        out_page = PageObject.create_blank_page(width=out_w, height=out_h)
        for slot, src_page in enumerate(chunk):
            if order_key == "从左到右":
                r, c = divmod(slot, cols)
            else:
                c, r = divmod(slot, rows)
            cell_x = margin + c * (avail_w + gap)
            cell_y = out_h - margin - (r + 1) * avail_h - r * gap
            src_w = float(src_page.mediabox.width)
            src_h = float(src_page.mediabox.height)
            scale = min(avail_w / max(1, src_w),
                        avail_h / max(1, src_h))
            placed_w = src_w * scale
            placed_h = src_h * scale
            x_off = cell_x + (avail_w - placed_w) / 2
            y_off = cell_y + (avail_h - placed_h) / 2
            transform = Transformation().scale(scale).translate(x_off, y_off)
            src_page.add_transformation(transform)
            src_page.mediabox.lower_left = (x_off, y_off)
            src_page.mediabox.upper_right = (x_off + placed_w,
                                             y_off + placed_h)
            out_page.merge_page(src_page)

        if draw_border:
            def paint(c, pw, ph):
                from reportlab.lib.colors import gray
                c.setStrokeColor(gray)
                c.setLineWidth(0.5)
                for rr in range(rows):
                    for cc in range(cols):
                        x = margin + cc * (avail_w + gap)
                        y = out_h - margin - (rr + 1) * avail_h - rr * gap
                        c.rect(x, y, avail_w, avail_h, fill=0, stroke=1)

            out_page.merge_page(_overlay_bytes(out_w, out_h, paint))
        writer.add_page(out_page)
        progress(f"N 合 1 拼版中：第 {sheet_start + 1}/{total} 页")

    _save(writer, output)
    out_pages = math.ceil(total / per_sheet)
    return f"已将 {total} 页拼为 {out_pages} 张纸，输出：{os.path.basename(output)}"
