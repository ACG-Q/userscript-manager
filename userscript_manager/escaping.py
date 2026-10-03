"""所有投影面（Issue 正文、Pages HTML）共用的转义工具。"""
from __future__ import annotations

import html


def escape_html(text: object) -> str:
    """HTML 文本/属性转义，含引号。"""
    return html.escape(str(text), quote=True)


def escape_md_cell(text: object) -> str:
    """Markdown 表格单元格转义：竖线变文本、换行变空格。"""
    return str(text).replace("|", "\\|").replace("\r\n", " ").replace("\n", " ")
