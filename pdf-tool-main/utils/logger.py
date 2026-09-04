# -*- coding: utf-8 -*-
"""统一日志模块：文件轮转、全局异常钩子、日志导出。"""

from __future__ import annotations

import logging
import os
import shutil
import sys
import threading
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.settings import PROJECT_DIR, get_settings


LOG_DIR = PROJECT_DIR / "logs"
LOG_FILE = LOG_DIR / "app.log"
_initialized = False


def _file_handler():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    size_mb = int(get_settings().get("log_max_mb", 5) or 5)
    handler = RotatingFileHandler(
        LOG_FILE, maxBytes=size_mb * 1024 * 1024,
        backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    return handler


def setup_logging():
    global _initialized
    logger = logging.getLogger("pdf_tool")
    if _initialized:
        return logger
    logger.setLevel(logging.INFO)
    enabled = bool(get_settings().get("log_to_file", True))
    if enabled and not any(isinstance(h, RotatingFileHandler)
                           for h in logger.handlers):
        logger.addHandler(_file_handler())
    logger.info("应用启动")
    _initialized = True
    sys.excepthook = _exception_hook
    threading.excepthook = _thread_exception_hook
    return logger


def get_logger():
    return logging.getLogger("pdf_tool")


def _exception_hook(exc_type, exc_value, tb):
    logger = get_logger()
    logger.error("未捕获异常：%s: %s\n%s",
                 exc_type.__name__, exc_value,
                 "".join(traceback.format_tb(tb)))


def _thread_exception_hook(args):
    get_logger().error(
        "线程异常：%s: %s\n%s",
        args.exc_type.__name__, args.exc_value,
        "".join(traceback.format_traceback(args.exc_traceback)))


def log_exception(context: str = ""):
    logger = get_logger()
    logger.exception(context or "业务异常")


def export_log(target: str) -> str:
    if not LOG_FILE.exists():
        raise RuntimeError("尚无日志可导出")
    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    shutil.copyfile(str(LOG_FILE), target)
    return target


def log_path() -> str:
    return str(LOG_FILE)
