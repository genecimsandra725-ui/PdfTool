#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PDF Tool 一键启动脚本。

用法：
    python bootstrap.py

脚本会自动完成：检测/创建 .venv -> 安装 requirements.txt -> 启动 main.py。
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).parent
VENV_DIR = PROJECT_DIR / ".venv"
REQUIREMENTS_FILE = PROJECT_DIR / "requirements.txt"
MAIN_FILE = PROJECT_DIR / "main.py"

# main.py 启动时需要导入渲染与文档转换模块；这些包同时保留在 requirements.txt 中。
RUNTIME_DEPENDENCIES = ("reportlab", "Pillow", "python-docx")


def log(message):
    """打印带前缀的步骤日志。"""
    print(f"[PDF Tool] {message}", flush=True)


def die(message):
    """打印错误信息后退出。"""
    print(f"\n[PDF Tool] 启动失败：{message}", file=sys.stderr)
    sys.exit(1)


def venv_layout():
    """按操作系统返回 .venv 内的解释器与 pip 路径。"""
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe", VENV_DIR / "Scripts" / "pip.exe"
    return VENV_DIR / "bin" / "python", VENV_DIR / "bin" / "pip"


def find_base_python():
    """寻找用于创建虚拟环境的系统 Python。"""
    if os.name == "nt":
        py_launcher = shutil.which("py")
        if py_launcher:
            log("检测到 Windows py 启动器，正在解析 Python 路径")
            try:
                result = subprocess.run(
                    [py_launcher, "-3", "-c", "import sys; print(sys.executable, end='')"],
                    capture_output=True,
                    text=True,
                )
            except OSError as exc:
                log(f"无法运行 py 启动器（{exc}），将尝试其他 Python")
            else:
                if result.returncode != 0:
                    log("py 启动器未找到可用的 Python 3，将尝试其他 Python")
                else:
                    candidate = Path(result.stdout.strip())
                    if candidate.exists():
                        return str(candidate)

    candidates = [sys.executable]
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            candidates.append(found)

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def run_command(command, description, error_message):
    """运行子进程并检查返回码。"""
    log(f"{description}：{' '.join(str(part) for part in command)}")
    try:
        result = subprocess.run(command, cwd=str(PROJECT_DIR))
    except OSError as exc:
        die(f"{error_message}（{exc}）")
    if result.returncode != 0:
        print(f"[PDF Tool] 命令返回码：{result.returncode}", file=sys.stderr)
        die(error_message)


def check_project_files():
    """启动前检查 requirements.txt 与 main.py 是否存在。"""
    if not REQUIREMENTS_FILE.is_file():
        die("未找到 requirements.txt，请确认脚本位于 PDF Tool 项目根目录")
    if not MAIN_FILE.is_file():
        die("未找到 main.py，请确认脚本位于 PDF Tool 项目根目录")


def prepare_venv(base_python):
    """检测 .venv，不存在或损坏时自动创建。"""
    python_path, _ = venv_layout()

    if not VENV_DIR.is_dir():
        log("未检测到 .venv 文件夹，开始创建 Python 虚拟环境")
        log(f"使用的系统 Python：{base_python}")
        run_command(
            [base_python, "-m", "venv", str(VENV_DIR)],
            "正在创建虚拟环境",
            "虚拟环境创建失败，请检查 Python venv 模块是否可用",
        )
    elif not python_path.exists():
        log("已检测到 .venv 文件夹，但解释器缺失，正在尝试修复虚拟环境")
        run_command(
            [base_python, "-m", "venv", str(VENV_DIR)],
            "正在修复虚拟环境",
            "虚拟环境修复失败，建议删除 .venv 文件夹后重试",
        )
    else:
        log("已检测到 .venv 虚拟环境，直接复用")


def install_requirements():
    """使用虚拟环境内的 pip 安装 requirements.txt 与运行必需依赖。"""
    python_path, pip_path = venv_layout()
    if not python_path.exists():
        die("虚拟环境 Python 解释器不存在，请重新运行本脚本")

    if pip_path.exists():
        pip_command = [
            str(pip_path),
            "install",
            "--disable-pip-version-check",
            "-r",
            str(REQUIREMENTS_FILE),
            *RUNTIME_DEPENDENCIES,
        ]
    else:
        log("未找到独立 pip 可执行文件，改用 python -m pip 安装")
        pip_command = [
            str(python_path),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "-r",
            str(REQUIREMENTS_FILE),
            *RUNTIME_DEPENDENCIES,
        ]

    run_command(
        pip_command,
        "正在安装依赖包（requirements.txt + GUI 运行必需依赖）",
        "依赖安装失败，请检查网络连接或 pip 配置后重试",
    )


def main():
    log("PDF Tool 一键启动程序")
    log("当前操作系统：" + ("Windows" if os.name == "nt" else "Linux/macOS"))
    log(f"项目目录：{PROJECT_DIR}")

    check_project_files()

    base_python = find_base_python()
    if not base_python:
        if os.name == "nt":
            die("未检测到 Python。请先安装 Python 3，并勾选 'Add python.exe to PATH'")
        die("未检测到 Python。请先安装 Python 3，或安装 python3 后重试")

    prepare_venv(base_python)
    install_requirements()

    python_path, _ = venv_layout()
    log("依赖安装完成，正在启动 PDF Tool GUI")
    run_command(
        [str(python_path), str(MAIN_FILE)],
        "正在启动程序",
        "PDF Tool 启动失败，请检查上方错误日志",
    )
    log("PDF Tool 已退出")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        die("用户中断了操作")
    except Exception as exc:  # noqa: BLE001 - 兜底捕获，保证给用户中文提示
        die(f"发生未预期的错误：{exc}")
