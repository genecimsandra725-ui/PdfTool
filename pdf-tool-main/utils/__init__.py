# -*- coding: utf-8 -*-
"""公共工具层：错误处理、路径、依赖检测、线程任务。"""

from .errors import AppError, error_text, translate_error
from .files import (ensure_dir, ensure_pdf_suffix, is_file_type,
                    safe_output_path, select_output_path)

__all__ = [
    "AppError", "error_text", "translate_error", "ensure_dir",
    "ensure_pdf_suffix", "is_file_type", "safe_output_path",
    "select_output_path",
]
