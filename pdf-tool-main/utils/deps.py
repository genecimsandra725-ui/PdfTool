# -*- coding: utf-8 -*-
"""外部依赖检测：Python 包、Tesseract、LibreOffice。"""

from __future__ import annotations

import importlib
import importlib.util
import os
import shutil
import sys

from .errors import AppError


def require_module(module: str, pip_name: str | None = None) -> object:
    try:
        return importlib.import_module(module)
    except ImportError as exc:
        package = pip_name or module
        raise AppError(
            f"缺少 Python 依赖 {package}，请重新运行 python bootstrap.py 安装后重试"
        ) from exc


def module_available(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def find_libreoffice() -> str | None:
    if os.name == "nt":
        candidates = [
            os.environ.get("ProgramFiles", r"C:\Program Files")
            + r"\LibreOffice\program\soffice.exe",
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
            + r"\LibreOffice\program\soffice.exe",
        ]
    elif sys.platform == "darwin":
        candidates = ["/Applications/LibreOffice.app/Contents/MacOS/soffice"]
    else:
        candidates = []
    for name in ("soffice", "libreoffice"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def require_libreoffice() -> str:
    path = find_libreoffice()
    if not path:
        raise AppError(
            "未检测到 LibreOffice，请先安装："
            "https://www.libreoffice.org/download/ ，安装后重试"
        )
    return path


def find_tesseract() -> str | None:
    if os.name == "nt":
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
    else:
        candidates = []
    found = shutil.which("tesseract")
    if found:
        return found
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def ocr_dependency_status() -> dict[str, bool]:
    """返回 OCR 相关依赖状态：pytesseract、Tesseract 程序、pdf2image。"""
    pt_ok = module_available("pytesseract")
    p2i_ok = module_available("pdf2image")
    return {
        "pytesseract": pt_ok,
        "tesseract": bool(find_tesseract()),
        "pdf2image": p2i_ok,
    }
