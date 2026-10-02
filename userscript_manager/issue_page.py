"""脚本 Issue 正文的唯一生成器：全量、幂等、可对账。

取舍（墓碑与 marker 解耦）：墓碑正文故意不携带 script-id 标记——
对账器据此把该 Issue 视为孤儿并关闭，墓碑一旦写入就不再被回写。
"""
import re

from .config import get_install_url
from .escaping import escape_md_cell

_MARKER_RE = re.compile(r"<!--\s*script-id:\s*([^\s>]+)\s*-->")


def build_marker(script_id: str) -> str:
    """生成正文首行的 script-id HTML 注释（对账依据）。"""
    return f"<!-- script-id: {script_id} -->"


def script_id_from_body(body: str) -> str | None:
    """从 Issue 正文提取 script-id；无标记返回 None。"""
    m = _MARKER_RE.search(body or "")
    return m.group(1) if m else None


def build_title(script: dict) -> str:
    """生成脚本 Issue 标题（📝 前缀 + 转义名称）。"""
    return f"📝 {escape_md_cell(script.get('name', script['id']))}"


def tombstone_title(title: str) -> str:
    """给孤儿 Issue 标题加 [已删除] 前缀（幂等）。"""
    return title if title.startswith("[已删除]") else f"[已删除] {title}"


def tombstone_body(name: str) -> str:
    """墓碑正文：保留历史讨论的说明，不再携带 script-id 标记。"""
    return f"> ⚠️ 脚本 `{escape_md_cell(name)}` 已从仓库删除。本页保留历史讨论，不再更新。\n"


def build_issue_body(script: dict) -> str:
    """渲染脚本 Issue 全文（标记/元数据表/文档/更新历史），幂等可对账。"""
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
