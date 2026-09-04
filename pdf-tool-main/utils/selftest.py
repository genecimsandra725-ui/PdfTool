# -*- coding: utf-8 -*-
"""程序自测：依赖、外部程序、目录权限、环境风险检测。"""

from __future__ import annotations

import importlib
import importlib.util
import os
import platform
import sys
from dataclasses import dataclass

from utils.deps import find_libreoffice, find_tesseract
from utils.settings import (PROJECT_DIR, SETTINGS_FILE, default_output_dir,
                            get_settings)


@dataclass
class CheckResult:
    status: str  # ok / warning / error
    title: str
    message: str


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _writable(path: str) -> bool:
    try:
        probe = os.path.join(path, ".write_test")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def run_selftest(progress=None) -> list[CheckResult]:
    """运行全部自测，返回风险点列表。"""
    if progress:
        progress("开始环境自测…")
    results: list[CheckResult] = []

    py = sys.version_info
    if py >= (3, 10):
        results.append(CheckResult("ok", "Python 版本",
                                   f"{platform.python_version()}"))
    else:
        results.append(CheckResult("error", "Python 版本",
                                   "需要 Python 3.10 或更高版本"))

    requirements = {
        "pypdf": "pypdf", "pymupdf": "PyMuPDF", "PIL": "Pillow",
        "reportlab": "reportlab", "docx": "python-docx",
        "pptx": "python-pptx", "openpyxl": "openpyxl",
        "PySide6": "PySide6", "qfluentwidgets": "PySide6-Fluent-Widgets",
        "pytesseract": "pytesseract", "pdf2image": "pdf2image",
    }
    for module, pip_name in requirements.items():
        ok = _module_available(module)
        results.append(CheckResult(
            "ok" if ok else "error",
            f"Python 依赖 {pip_name}",
            "已安装" if ok else "缺失，请运行 python bootstrap.py"))

    tess = find_tesseract()
    results.append(CheckResult(
        "ok" if tess else "warning",
        "Tesseract OCR",
        tess or "未检测到，OCR 功能不可用"))
    lo = find_libreoffice()
    results.append(CheckResult(
        "ok" if lo else "warning",
        "LibreOffice",
        lo or "未检测到，Office 转 PDF 功能不可用"))

    checks = [
        ("源码目录可写", str(PROJECT_DIR)),
        ("日志目录可写", str(PROJECT_DIR / "logs")),
        ("配置文件目录可写", str(SETTINGS_FILE.parent)),
        ("默认输出目录可写", default_output_dir()),
    ]
    for title, path in checks:
        os.makedirs(path, exist_ok=True) if title == "日志目录可写" else None
        ok = _writable(path)
        results.append(CheckResult(
            "ok" if ok else "error", title,
            "可写" if ok else f"无写入权限：{path}"))

    venv_python = (PROJECT_DIR / ".venv" /
                   ("Scripts/python.exe" if os.name == "nt" else "bin/python"))
    results.append(CheckResult(
        "ok" if venv_python.exists() else "warning",
        ".venv 虚拟环境",
        str(venv_python) if venv_python.exists() else
        "未检测到 .venv，运行 python bootstrap.py 会自动创建"))

    try:
        from ui.main_window import MainWindow
        importable = bool(MainWindow)
    except Exception as exc:
        importable = False
        results.append(CheckResult("error", "UI 模块导入",
                                   f"main_window 无法导入：{exc}"))
    if importable:
        results.append(CheckResult("ok", "UI 模块导入", "主窗口模块可正常导入"))

    if progress:
        progress("自测完成")
    return results


def risk_summary(results: list[CheckResult]) -> str:
    errors = [r for r in results if r.status == "error"]
    warnings = [r for r in results if r.status == "warning"]
    if not errors and not warnings:
        return "未发现风险点"
    return f"发现 {len(errors)} 个错误、{len(warnings)} 个警告"
