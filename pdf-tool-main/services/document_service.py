# -*- coding: utf-8 -*-
"""文档互转服务：图片转 PDF、Office 转 PDF。"""

from __future__ import annotations

import io
import os
import subprocess
from collections.abc import Callable

from utils.deps import require_libreoffice, require_module
from utils.errors import AppError
from utils.files import ensure_dir, ensure_pdf_suffix

ProgressFn = Callable[[str], None]
_NOOP: ProgressFn = lambda msg: None

PAGE_SIZES = {
    "原始尺寸": None,
    "A4 纵向": (595.28, 841.89),
    "A4 横向": (841.89, 595.28),
    "Letter 纵向": (612.0, 792.0),
    "Letter 横向": (792.0, 612.0),
}


def images_to_pdf(paths: list[str], output: str, size_name: str = "原始尺寸",
                  progress: ProgressFn = _NOOP) -> str:
    fitz = require_module("pymupdf", "PyMuPDF")
    Image = require_module("PIL", "Pillow").Image
    output = ensure_pdf_suffix(output)
    ensure_dir(os.path.dirname(os.path.abspath(output)) or ".")
    doc = fitz.open()
    try:
        for idx, path in enumerate(paths, start=1):
            if not os.path.isfile(path):
                raise AppError(f"图片不存在：{path}")
            with Image.open(path) as img:
                iw, ih = img.size
                info = dict(img.info)
                stream = io.BytesIO()
                if img.mode in ("RGBA", "LA", "P"):
                    img.convert("RGBA").save(stream, format="PNG")
                else:
                    img.convert("RGB").save(stream, format="PNG")
                data = stream.getvalue()
            preset = PAGE_SIZES.get(size_name)
            if preset:
                pw, ph = preset
                scale = min(pw / max(1, iw), ph / max(1, ih))
                dw, dh = iw * scale, ih * scale
                rect = fitz.Rect((pw - dw) / 2, (ph - dh) / 2,
                                 (pw + dw) / 2, (ph + dh) / 2)
                page = doc.new_page(width=pw, height=ph)
            else:
                dpi = float((info.get("dpi") or (72, 72))[0] or 72)
                pw = iw * 72 / dpi
                ph = ih * 72 / dpi
                page = doc.new_page(width=pw, height=ph)
                rect = fitz.Rect(0, 0, pw, ph)
            page.insert_image(rect, stream=data)
            progress(f"已加入第 {idx}/{len(paths)} 张图片")
        doc.save(output, garbage=3, deflate=True)
    finally:
        doc.close()
    return f"已生成 PDF：{os.path.basename(output)}"


def office_to_pdf_batch(paths: list[str], outdir: str,
                        progress: ProgressFn = _NOOP) -> str:
    soffice = require_libreoffice()
    outdir = ensure_dir(outdir)
    count = 0
    for i, src in enumerate(paths, start=1):
        if not os.path.isfile(src):
            raise AppError(f"文件不存在：{src}")
        progress(f"（{i}/{len(paths)}）正在转换 {os.path.basename(src)}…")
        cmd = [soffice, "--headless", "--norestore", "--convert-to", "pdf",
               "--outdir", outdir, src]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=600)
        except subprocess.TimeoutExpired as exc:
            raise AppError(f"LibreOffice 转换超时：{os.path.basename(src)}"
                           ) from exc
        except OSError as exc:
            raise AppError(f"无法启动 LibreOffice：{exc}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise AppError(
                f"LibreOffice 转换失败：{detail[:500]}")
        stem = os.path.splitext(os.path.basename(src))[0]
        expected = os.path.join(outdir, stem + ".pdf")
        if not os.path.isfile(expected):
            raise AppError("LibreOffice 未生成 PDF，请检查源文件是否损坏")
        count += 1
        progress(f"✓ 已生成 {os.path.basename(expected)}")
    return f"已转换 {count} 个 Office 文件，输出位置：{outdir}"
