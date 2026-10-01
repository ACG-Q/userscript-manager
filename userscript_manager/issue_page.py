"""脚本 Issue 正文的唯一生成器：全量、幂等、可对账。"""
import re

from .config import get_install_url
from .escaping import escape_md_cell

_MARKER_RE = re.compile(r"<!--\s*script-id:\s*([^\s>]+)\s*-->")


def build_marker(script_id: str) -> str:
    return f"<!-- script-id: {script_id} -->"


def script_id_from_body(body: str) -> str | None:
    m = _MARKER_RE.search(body or "")
    return m.group(1) if m else None


def build_title(script: dict) -> str:
    return f"📝 {escape_md_cell(script.get('name', script['id']))}"


def tombstone_title(title: str) -> str:
    return title if title.startswith("[已删除]") else f"[已删除] {title}"


def tombstone_body(name: str) -> str:
    return f"> ⚠️ 脚本 `{escape_md_cell(name)}` 已从仓库删除。本页保留历史讨论，不再更新。\n"


def build_issue_body(script: dict) -> str:
    sid = script["id"]
    name = escape_md_cell(script.get("name", sid))
    version = escape_md_cell(script.get("version", ""))
    author = escape_md_cell(script.get("author", "") or "-")
    match_rules = ", ".join(f"`{escape_md_cell(m)}`" for m in script.get("match") or ["*://*/*"])
    install_url = get_install_url(sid)
    documentation = script.get("documentation") or "_暂无文档_"

    lines = [
        build_marker(sid),
        "",
        f"## {name}",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 名称 | {name} |",
        f"| 版本 | {version} |",
        f"| 作者 | {author} |",
        f"| 匹配规则 | {match_rules} |",
        f"| 安装链接 | [安装脚本]({install_url}) |",
        "",
        "## 文档",
        "",
        documentation,
        "",
        "## 更新历史",
        "",
        "| 版本 | 日期 | 说明 |",
        "| --- | --- | --- |",
    ]
    rows = script.get("changelog") or []
    if rows:
        for row in rows:
            lines.append(
                f"| {escape_md_cell(row.get('version', ''))} "
                f"| {escape_md_cell(row.get('date', ''))} "
                f"| {escape_md_cell(row.get('note', ''))} |"
            )
    else:
        lines.append("| - | - | 暂无更新记录 |")
    lines.append("")
    return "\n".join(lines)
