# -*- coding: utf-8 -*-
"""QFluentWidgets 版文档互转页面。"""

from __future__ import annotations

from services import convert_service
from ui.pages.pdf_tools import ParamSpec, ToolSpec, build_page
from ui.common.tool_page import ToolPage


def _batch_job(kind: str):
    def job(paths, outdir, values, progress):
        return convert_service.batch_pdf_to_dir(
            paths, outdir, kind, progress)
    return job


def _pdf_image_job(paths, outdir, values, progress):
    total = 0
    mode = "all" if values["mode"] == "全部页面" else "single"
    for src in paths:
        total += convert_service.pdf_to_images(
            src, outdir, mode=mode, page_number=int(values["page"]),
            fmt=values["format"], zoom=int(values["zoom"]), progress=progress)
    return f"已导出 {total} 张图片，输出位置：{outdir}"


def _page(title, desc, kind):
    return build_page(ToolSpec(
        title=title, description=desc,
        job=_batch_job(kind), output_kind="dir", single_mode=False,
        object_name=f"convert_{kind.lower()}"))


def pdf_to_image_page():
    return build_page(ToolSpec(
        title="PDF 转图片",
        description="将 PDF 页面渲染为 PNG/JPG 图片。",
        job=_pdf_image_job, output_kind="dir", single_mode=False,
        params=(
            ParamSpec("mode", "导出范围", "combo",
                      ("全部页面", "指定单页"), "全部页面"),
            ParamSpec("page", "指定页码", "spin", default_value=1,
                      minimum=1),
            ParamSpec("format", "图片格式", "combo",
                      ("PNG", "JPG"), "PNG"),
            ParamSpec("zoom", "缩放倍数", "spin", default_value=2,
                      minimum=1, maximum=6),
        ),
        object_name="convert_pdf_images"))


def doc_conversion_pages() -> list[ToolPage]:
    return [
        _page("PDF 转 Word", "提取文本与基础布局生成 Word。", "Word"),
        _page("PDF 转 Excel", "提取文本与表格生成 Excel。", "Excel"),
        _page("PDF 转 PPT", "按页渲染生成演示文稿。", "PPT"),
        _page("PDF 转 TXT", "导出全部页面文本。", "TXT"),
        _page("PDF 转 HTML", "导出文本与内嵌图片为 HTML。", "HTML"),
        _page("PDF 转 EPUB", "将 PDF 页面打包为 EPUB。", "EPUB"),
        pdf_to_image_page(),
    ]
