# -*- coding: utf-8 -*-
"""
HTML 演示文稿模板包
==================

提供预置的演示文稿样式模板，供 html_generate 工具使用。

可用模板：
- dark_botanical:优雅深色主题，适合正式场合
"""

from .dark_botanical import (
    DARK_BOTANICAL_TEMPLATE,
    generate_slide_title,
    generate_slide_data,
    generate_slide_trends,
    generate_slide_content,
)

__all__ = [
    "DARK_BOTANICAL_TEMPLATE",
    "generate_slide_title",
    "generate_slide_data",
    "generate_slide_trends",
    "generate_slide_content",
]