# -*- coding: utf-8 -*-
"""统一业务异常与用户可读错误转换。"""

from __future__ import annotations

import contextlib
import os


class AppError(Exception):
    """业务层可预期异常，界面统一展示给用户。"""


def translate_error(exc: BaseException, context: str = "") -> str:
    """把底层异常转成适合弹窗展示的中文信息。"""
    if isinstance(exc, AppError):
        message = str(exc)
    elif isinstance(exc, PermissionError):
        message = f"没有写入权限：{getattr(exc, 'filename', '') or exc}"
    elif isinstance(exc, FileNotFoundError):
        message = f"文件不存在：{getattr(exc, 'filename', '') or exc}"
    elif isinstance(exc, OSError):
        message = f"系统错误：{exc}"
    else:
        message = f"{exc}"
    return f"{context}：{message}" if context else message


def error_text(exc: BaseException) -> str:
    return translate_error(exc)


def get_file_size_text(path: str) -> str:
    """返回适合界面展示的文件大小。"""
    with contextlib.suppress(OSError):
        size = os.path.getsize(path)
        if size < 1024:
            return f"{size} B"
        if size < 1024 ** 2:
            return f"{size / 1024:.1f} KB"
        return f"{size / 1024 ** 2:.2f} MB"
    return ""
