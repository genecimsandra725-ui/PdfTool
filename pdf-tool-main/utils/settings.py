# -*- coding: utf-8 -*-
"""项目本地 JSON 配置。"""

from __future__ import annotations

import json
import os
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
SETTINGS_FILE = PROJECT_DIR / "settings.json"

DEFAULTS = {
    "auto_selftest_on_startup": True,
    "log_to_file": True,
    "log_max_mb": 5,
    "sidebar_width": 160,
    "nav_font_size": 11,
    "nav_padding_h": 6,
    "nav_padding_v": 3,
    "action_font_size": 10,
    "action_height": 22,
    "window_width": 940,
    "window_height": 620,
    "content_margin": 16,
    "content_spacing": 6,
    "log_height": 92,
}


def _load() -> dict:
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    merged = dict(DEFAULTS)
    merged.update({k: v for k, v in data.items() if k in DEFAULTS})
    return merged


def get_settings() -> dict:
    return _load()


def save_settings(values: dict):
    data = _load()
    for key, value in values.items():
        if key in DEFAULTS:
            data[key] = value
    try:
        SETTINGS_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"无法写入配置文件 settings.json：{exc}") from exc


def workspace_path() -> str:
    return str(PROJECT_DIR)


def default_output_dir() -> str:
    return os.path.expanduser("~/Desktop")
