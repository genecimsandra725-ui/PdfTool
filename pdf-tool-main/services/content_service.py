# -*- coding: utf-8 -*-
"""文本/图片内容服务：信息、提取文本、提取图片、对比、OCR。"""

from __future__ import annotations

import difflib
import io
import os
from collections.abc import Callable

from utils.deps import require_module
from utils.errors import AppError
from utils.files import ensure_dir

ProgressFn = Callable[[str], None]
_NOOP: ProgressFn = lambda msg: None


def _reader(src: str):
    PdfReader = require_module("pypdf").PdfReader
    if not os.path.isfile(src):
        raise AppError(f"文件不存在：{src}")
    reader = PdfReader(src)
    if reader.is_encrypted:
        raise AppError(f"PDF“{os.path.basename(src)}”已加密，请先移除密码")
    return reader


def _page_indices(total: int, mode: str = "all",
                  from_page: int = 1, to_page: int = 1):
    if mode == "all":
        return list(range(total))
    return list(range(max(0, from_page - 1), min(total, to_page)))


def extract_pages_text(src: str, mode: str = "all",
                       from_page: int = 1, to_page: int = 1,
                       progress: ProgressFn = _NOOP) -> tuple[str, int]:
    """返回提取文本和实际处理页数。"""
    reader = _reader(src)
    indices = _page_indices(len(reader.pages), mode, from_page, to_page)
    parts = []
    for page_no in indices:
        text = reader.pages[page_no].extract_text() or ""
        parts.append(f"======== 第 {page_no + 1} 页 ========\n\n{text.strip()}")
        progress(f"已提取第 {page_no + 1} 页")
    return "\n\n".join(parts), len(indices)


def export_text_txt(src: str, outdir: str, mode: str = "all",
                    from_page: int = 1, to_page: int = 1,
                    progress: ProgressFn = _NOOP) -> str:
    text, _ = extract_pages_text(src, mode, from_page, to_page, progress)
    if not text.strip():
        raise AppError("未提取到文本，可能是扫描版 PDF")
    stem = os.path.splitext(os.path.basename(src))[0]
    outdir = ensure_dir(outdir)
    out = os.path.join(outdir, stem + ".txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(text)
    return f"TXT 文本已导出：{os.path.basename(out)}"


def export_text_docx(src: str, outdir: str, mode: str = "all",
                     from_page: int = 1, to_page: int = 1,
                     progress: ProgressFn = _NOOP) -> str:
    reader = _reader(src)
    indices = _page_indices(len(reader.pages), mode, from_page, to_page)
    Document = require_module("docx", "python-docx").Document
    doc = Document()
    for page_no in indices:
        text = reader.pages[page_no].extract_text() or ""
        doc.add_heading(f"第 {page_no + 1} 页", level=2)
        doc.add_paragraph(text.strip() or "（此页无文本）")
        progress(f"正在写入第 {page_no + 1} 页")
    stem = os.path.splitext(os.path.basename(src))[0]
    outdir = ensure_dir(outdir)
    out = os.path.join(outdir, stem + ".docx")
    doc.save(out)
    return f"DOCX 文本已导出：{os.path.basename(out)}"


def extract_images(
    src: str,
    outdir: str,
    formats: tuple[str, ...] = ("PNG", "JPG"),
    quality: int = 85,
    mode: str = "all",
    from_page: int = 1,
    to_page: int = 1,
    progress: ProgressFn = _NOOP,
) -> str:
    """导出 PDF 页面内嵌图片。"""
    Image = require_module("PIL", "Pillow").Image
    reader = _reader(src)
    indices = _page_indices(len(reader.pages), mode, from_page, to_page)
    stem = os.path.splitext(os.path.basename(src))[0]
    outdir = ensure_dir(outdir)
    count = 0
    for page_no in indices:
        page = reader.pages[page_no]
        for img_no, img_obj in enumerate(page.images, start=1):
            img = Image.open(io.BytesIO(img_obj.data))
            base = os.path.join(outdir, f"{stem}_第{page_no + 1}页_图片{img_no}")
            if "PNG" in formats:
                img.convert("RGBA").save(base + ".png", "PNG")
            if "JPG" in formats:
                img.convert("RGB").save(base + ".jpg", "JPEG", quality=quality)
            if "TIFF" in formats:
                img.convert("RGBA").save(base + ".tiff", "TIFF")
            if "WebP" in formats:
                img.convert("RGBA").save(base + ".webp", "WEBP",
                                         quality=quality)
            count += 1
            progress(f"已导出第 {count} 张图片")
    if not count:
        raise AppError("所选页面中未找到可导出的图片")
    return f"已导出 {count} 张图片，输出位置：{outdir}"


def pdf_info(src: str) -> str:
    reader = _reader(src)
    meta = reader.metadata or {}
    lines = [
        f"文件：{os.path.basename(src)}",
        f"页数：{len(reader.pages)}",
        f"标题：{meta.get('/Title', '—')}",
        f"作者：{meta.get('/Author', '—')}",
        f"创建程序：{meta.get('/Creator', '—')}",
        f"生成程序：{meta.get('/Producer', '—')}",
        f"创建时间：{meta.get('/CreationDate', '—')}",
        f"加密：{'是' if reader.is_encrypted else '否'}",
    ]
    return "\n".join(lines)


def compare_pdfs(path_a: str, path_b: str,
                 progress: ProgressFn = _NOOP) -> str:
    reader_a = _reader(path_a)
    reader_b = _reader(path_b)
    pages_a = len(reader_a.pages)
    pages_b = len(reader_b.pages)
    out = [
        f"PDF A：{os.path.basename(path_a)}（{pages_a} 页）",
        f"PDF B：{os.path.basename(path_b)}（{pages_b} 页）",
        "",
    ]
    diffs = 0
    for i in range(max(pages_a, pages_b)):
        out.append(f"── 第 {i + 1} 页 ──")
        if i >= pages_a:
            text_b = (reader_b.pages[i].extract_text() or "").splitlines()
            out += [f"+ {line}" for line in text_b]
            diffs += 1
            continue
        if i >= pages_b:
            text_a = (reader_a.pages[i].extract_text() or "").splitlines()
            out += [f"- {line}" for line in text_a]
            diffs += 1
            continue
        text_a = (reader_a.pages[i].extract_text() or "").splitlines()
        text_b = (reader_b.pages[i].extract_text() or "").splitlines()
        diff = list(difflib.unified_diff(text_a, text_b, lineterm="", n=1))
        if diff:
            out.append(f"（差异 {len(diff)} 行）")
            out.extend(diff[2:])
            diffs += 1
        else:
            out.append("内容一致")
        progress(f"已比较 {i + 1}/{max(pages_a, pages_b)} 页")
    summary = ("未发现差异" if diffs == 0
               else f"共有 {diffs} 页存在差异")
    out.append("")
    out.append(summary)
    return "\n".join(out)


def ocr_pdf(src: str, output: str, lang: str = "eng", dpi: int = 300,
            progress: ProgressFn = _NOOP) -> str:
    """扫描版 PDF OCR；需要 pytesseract、pdf2image、Tesseract。"""
    from utils.deps import find_tesseract
    require_module("pytesseract")
    require_module("pdf2image")
    if not find_tesseract():
        raise AppError(
            "未检测到 Tesseract OCR，请先安装后重试，"
            "Windows：https://github.com/UB-Mannheim/tesseract/wiki")
    pytesseract = require_module("pytesseract")
    if find_tesseract():
        pytesseract.pytesseract.tesseract_cmd = find_tesseract()
    convert_from_path = require_module("pdf2image").convert_from_path
    writer_mod = require_module("pypdf")

    output = output if output.lower().endswith(".pdf") else output + ".pdf"
    progress("正在将 PDF 页面渲染为图片…")
    images = convert_from_path(src, dpi=dpi)
    writer = writer_mod.PdfWriter()
    for i, img in enumerate(images, start=1):
        progress(f"正在 OCR 第 {i}/{len(images)} 页…")
        pdf_bytes = pytesseract.image_to_pdf_or_hocr(
            img, extension="pdf", lang=lang)
        reader = writer_mod.PdfReader(io.BytesIO(pdf_bytes))
        writer.add_page(reader.pages[0])
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"OCR 完成，共 {len(images)} 页，输出：{os.path.basename(output)}"
