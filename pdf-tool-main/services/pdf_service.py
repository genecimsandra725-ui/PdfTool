# -*- coding: utf-8 -*-
"""基础 PDF 处理服务：合并、拆分、压缩、旋转、裁剪、修复、密码等。"""

from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime
from typing import Any

from utils.errors import AppError
from utils.files import ensure_dir, ensure_pdf_suffix

ProgressFn = Callable[[str], None]
_NOOP: ProgressFn = lambda msg: None


def _pypdf():
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError as exc:
        raise AppError("缺少 pypdf 依赖，请重新运行 python bootstrap.py") from exc
    return PdfReader, PdfWriter


def _open_reader(src: str):
    PdfReader, _ = _pypdf()
    if not os.path.isfile(src):
        raise AppError(f"文件不存在：{src}")
    try:
        reader = PdfReader(src)
    except Exception as exc:
        raise AppError(f"无法打开 PDF：{os.path.basename(src)}（{exc}）") from exc
    if reader.is_encrypted:
        raise AppError(
            f"PDF“{os.path.basename(src)}”已加密，请先用“密码保护”移除密码")
    return reader


def page_count(src: str) -> int:
    return len(_open_reader(src).pages)


def merge_pdfs(inputs: list[str], output: str,
               progress: ProgressFn = _NOOP) -> str:
    if len(inputs) < 2:
        raise AppError("请至少选择 2 个 PDF 文件")
    output = ensure_pdf_suffix(output)
    ensure_dir(os.path.dirname(output) or ".")
    _, PdfWriter = _pypdf()
    writer = PdfWriter()
    for index, path in enumerate(inputs, start=1):
        progress(f"正在读取 {os.path.basename(path)}…")
        writer.append(path)
    progress("正在写入合并结果…")
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"合并完成，已生成 {os.path.basename(output)}"


def split_pdf(src: str, outdir: str, mode: str = "all",
              from_page: int = 1, to_page: int = 1,
              progress: ProgressFn = _NOOP) -> str:
    reader = _open_reader(src)
    total = len(reader.pages)
    outdir = ensure_dir(outdir)
    stem = os.path.splitext(os.path.basename(src))[0]
    _, PdfWriter = _pypdf()
    pages = (range(total) if mode == "all"
             else range(max(0, from_page - 1), min(total, to_page)))
    count = 0
    for i in pages:
        writer = PdfWriter()
        writer.add_page(reader.pages[i])
        name = os.path.join(outdir, f"{stem}_第{i + 1}页.pdf")
        with open(name, "wb") as fh:
            writer.write(fh)
        count += 1
        progress(f"已保存第 {i + 1} 页")
    if count == 0:
        raise AppError("没有可保存的页面，请检查页码范围")
    return f"已保存 {count} 个页面，输出位置：{outdir}"


def compress_pdf(src: str, output: str, compress_streams: bool = True,
                 remove_duplicates: bool = True,
                 strip_metadata: bool = False,
                 progress: ProgressFn = _NOOP) -> str:
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    _, PdfWriter = _pypdf()
    writer = PdfWriter()
    total = len(reader.pages)
    for i, page in enumerate(reader.pages, start=1):
        writer.add_page(page)
        if compress_streams:
            writer.pages[-1].compress_content_streams()
        if i % 10 == 0:
            progress(f"正在压缩第 {i}/{total} 页")
    if remove_duplicates:
        writer.compress_identical_objects(remove_identicals=True,
                                          remove_orphans=True)
    if not strip_metadata and reader.metadata:
        writer.add_metadata(reader.metadata)
    with open(output, "wb") as fh:
        writer.write(fh)
    before = os.path.getsize(src)
    after = os.path.getsize(output)
    percent = (1 - after / before) * 100 if before else 0
    progress(f"压缩完成：{before / 1024:.1f} KB → {after / 1024:.1f} KB")
    return f"压缩完成，体积变化 {percent:+.1f}%，输出：{os.path.basename(output)}"


def rotate_pdf(src: str, output: str, angle: int = 90,
               mode: str = "all", from_page: int = 1, to_page: int = 1,
               specific: str = "",
               progress: ProgressFn = _NOOP) -> str:
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    total = len(reader.pages)
    _, PdfWriter = _pypdf()
    if mode == "all":
        indices = set(range(total))
    elif mode == "range":
        indices = set(range(max(0, from_page - 1), min(total, to_page)))
    else:
        indices = set()
        for part in specific.split(","):
            part = part.strip()
            if "-" in part:
                a, b = part.split("-", 1)
                indices.update(range(int(a) - 1, min(int(b), total)))
            elif part.isdigit():
                indices.add(int(part) - 1)
        if not indices:
            raise AppError("未输入有效的页码")
    writer = PdfWriter()
    for i, page in enumerate(reader.pages):
        if i in indices:
            page.rotate(angle)
        writer.add_page(page)
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"已将 {len(indices)} 页旋转 {angle}°，输出：{os.path.basename(output)}"


def crop_pdf(src: str, output: str, top: float = 0, bottom: float = 0,
             left: float = 0, right: float = 0, mode: str = "all",
             from_page: int = 1, to_page: int = 1,
             progress: ProgressFn = _NOOP) -> str:
    output = ensure_pdf_suffix(output)
    mm = 2.8346
    reader = _open_reader(src)
    total = len(reader.pages)
    _, PdfWriter = _pypdf()
    writer = PdfWriter()
    if mode == "all":
        indices = set(range(total))
    else:
        indices = set(range(max(0, from_page - 1), min(total, to_page)))
    for i, page in enumerate(reader.pages):
        if i in indices:
            mb = page.mediabox
            mb.left = float(mb.left) + left * mm
            mb.bottom = float(mb.bottom) + bottom * mm
            mb.right = float(mb.right) - right * mm
            mb.top = float(mb.top) - top * mm
        writer.add_page(page)
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"已裁剪 {len(indices)} 页，输出：{os.path.basename(output)}"


def protect_pdf(src: str, output: str, user_password: str,
                owner_password: str | None = None,
                algorithm: str = "AES-256",
                progress: ProgressFn = _NOOP) -> str:
    if not user_password:
        raise AppError("打开密码不能为空")
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    _, PdfWriter = _pypdf()
    writer = PdfWriter()
    writer.append(reader)
    writer.encrypt(user_password=user_password,
                   owner_password=owner_password or user_password,
                   algorithm=algorithm)
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"加密完成，算法：{algorithm}，输出：{os.path.basename(output)}"


def remove_pdf_password(src: str, output: str, password: str = "",
                        progress: ProgressFn = _NOOP) -> str:
    output = ensure_pdf_suffix(output)
    PdfReader, PdfWriter = _pypdf()
    reader = PdfReader(src)
    if reader.is_encrypted:
        result = reader.decrypt(password)
        if getattr(result, "value", None) == 0:
            raise AppError("密码错误，无法移除加密")
    writer = PdfWriter()
    writer.append(reader)
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"已移除密码，输出：{os.path.basename(output)}"


def remove_blank_pages(src: str, output: str, threshold: int = 100,
                       progress: ProgressFn = _NOOP) -> str:
    reader = _open_reader(src)
    _, PdfWriter = _pypdf()
    writer = PdfWriter()
    blank = []
    for i, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if len(text) < threshold:
            blank.append(i - 1)
            progress(f"第 {i} 页判定为空白页")
        else:
            writer.add_page(page)
    output = ensure_pdf_suffix(output)
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"已删除 {len(blank)} 个空白页，输出：{os.path.basename(output)}"


def repair_pdf(src: str, output: str, strict: bool = False,
               copy_metadata: bool = True,
               progress: ProgressFn = _NOOP) -> str:
    output = ensure_pdf_suffix(output)
    if not os.path.isfile(src):
        raise AppError(f"文件不存在：{src}")
    PdfReader, PdfWriter = _pypdf()
    reader = PdfReader(src, strict=strict)
    writer = PdfWriter()
    total = len(reader.pages)
    bad = []
    for i in range(total):
        try:
            writer.add_page(reader.pages[i])
            if (i + 1) % 10 == 0:
                progress(f"已处理 {i + 1}/{total} 页")
        except Exception as exc:
            bad.append(i + 1)
            progress(f"跳过损坏的第 {i + 1} 页：{exc}")
    if copy_metadata:
        try:
            writer.add_metadata(reader.metadata or {})
        except Exception:
            pass
    with open(output, "wb") as fh:
        writer.write(fh)
    ok = total - len(bad)
    return f"修复完成：成功恢复 {ok}/{total} 页" + (
        f"，跳过页面：{bad}" if bad else "")


def reorder_pdf(src: str, output: str, page_order: list[int],
                progress: ProgressFn = _NOOP) -> str:
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    _, PdfWriter = _pypdf()
    writer = PdfWriter()
    for index in page_order:
        if 0 <= index < len(reader.pages):
            writer.add_page(reader.pages[index])
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"已按新顺序保存 {len(page_order)} 页"


METADATA_FIELDS = (
    ("/Title", "标题"), ("/Author", "作者"), ("/Subject", "主题"),
    ("/Keywords", "关键词"), ("/Creator", "创建程序"),
    ("/Producer", "生成程序"),
)


def metadata_fields(src: str) -> tuple[dict[str, str], int]:
    reader = _open_reader(src)
    meta = reader.metadata or {}
    fields = {key: str(meta.get(key) or "") for key, _ in METADATA_FIELDS}
    return fields, len(reader.pages)


def save_metadata(src: str, output: str, fields: dict[str, str],
                  progress: ProgressFn = _NOOP) -> str:
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    _, PdfWriter = _pypdf()
    writer = PdfWriter()
    writer.append(reader)
    meta = {key: value for key, value in fields.items() if value.strip()}
    meta["/ModDate"] = datetime.now().strftime("D:%Y%m%d%H%M%S")
    writer.add_metadata(meta)
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"元数据已保存，输出：{os.path.basename(output)}"


def read_bookmarks(src: str) -> tuple[list[tuple[int, str, int]], int]:
    """返回 (缩进, 标题, 0 基页码) 列表及总页数。"""
    reader = _open_reader(src)
    flat: list[tuple[int, str, int]] = []

    def walk(outline, depth):
        for item in outline:
            if isinstance(item, list):
                walk(item, depth + 1)
            else:
                try:
                    page = reader.get_destination_page_number(item)
                except Exception:
                    page = 0
                flat.append((depth, item.title, page))

    walk(reader.outline, 0)
    return flat, len(reader.pages)


def save_bookmarks(src: str, output: str,
                   bookmarks: list[tuple[int, str, int]],
                   progress: ProgressFn = _NOOP) -> str:
    output = ensure_pdf_suffix(output)
    reader = _open_reader(src)
    _, PdfWriter = _pypdf()
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    for _, title, page in bookmarks:
        writer.add_outline_item(title, page)
    with open(output, "wb") as fh:
        writer.write(fh)
    return f"书签已保存，共 {len(bookmarks)} 条"


def split_by_bookmarks(src: str, outdir: str,
                       progress: ProgressFn = _NOOP) -> str:
    flat, total = read_bookmarks(src)
    top = [(title, page) for depth, title, page in flat if depth == 0]
    if not top:
        raise AppError("未找到一级书签")
    outdir = ensure_dir(outdir)
    reader = _open_reader(src)
    _, PdfWriter = _pypdf()
    count = 0
    for i, (title, start) in enumerate(top):
        end = top[i + 1][1] if i + 1 < len(top) else total
        writer = PdfWriter()
        for page_index in range(start, end):
            writer.add_page(reader.pages[page_index])
        safe = "".join(c for c in title if c.isalnum() or c in " _-").strip()
        name = os.path.join(outdir, f"{i + 1:02d}_{safe or '章节'}.pdf")
        with open(name, "wb") as fh:
            writer.write(fh)
        count += 1
        progress(f"已生成：{os.path.basename(name)}")
    return f"已按书签拆分为 {count} 个文件，输出位置：{outdir}"
