# -*- coding: utf-8 -*-
"""路径、文件类型与输出目录公共工具。"""

from __future__ import annotations

import os
import re
from pathlib import Path


IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp")
PDF_EXTS = (".pdf",)
OFFICE_EXTS = (".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
               ".odt", ".ods", ".odp")


def is_file_type(path: str, exts) -> bool:
    return os.path.isfile(path) and path.lower().endswith(tuple(exts))


def ensure_dir(path: str) -> str:
    """创建目录（若不存在），返回绝对路径。"""
    path = os.path.abspath(path)
    os.makedirs(path, exist_ok=True)
    return path


def ensure_pdf_suffix(path: str) -> str:
    return path if path.lower().endswith(".pdf") else path + ".pdf"


def safe_output_path(directory: str, stem: str, suffix: str) -> str:
    directory = ensure_dir(directory)
    return os.path.join(directory, f"{stem}{suffix}")


def select_output_path(directory: str, stem: str, suffix: str) -> str:
    """返回不覆盖已有文件的输出路径，若冲突自动追加序号。"""
    base = os.path.join(ensure_dir(directory), f"{stem}{suffix}")
    if not os.path.exists(base):
        return base
    name = Path(base).stem
    parent = os.path.dirname(base)
    for index in range(2, 1000):
        candidate = os.path.join(parent, f"{name}_{index}{suffix}")
        if not os.path.exists(candidate):
            return candidate
    raise RuntimeError("无法生成不冲突的输出文件名")


def filter_dropped_paths(data: str, exts) -> list[str]:
    """Qt 拖放文件数据转路径列表，并过滤扩展名。"""
    raw = re.findall(r"\{([^}]+)\}", data)
    plain = re.sub(r"\{[^}]+\}", "", data).strip()
    if plain:
        raw += plain.split()
    result = []
    for item in raw:
        path = item.strip()
        if path and path.lower().endswith(tuple(exts)):
            result.append(os.path.normpath(path))
    return result
