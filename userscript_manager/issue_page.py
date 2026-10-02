"""脚本 Issue / 版本帖正文的唯一生成器：全量、幂等、可对账。

分工（D5/D6）：Issue 正文只承载活字段与版本帖索引；文档与更新历史
只出现在版本帖快照与脚本详情页。墓碑正文故意不携带 script-id 标记——
对账器据此把该 Issue 视为孤儿并关闭，墓碑一旦写入就不再被回写。
"""
import re
from datetime import date

from .config import get_install_url, get_pages_base_url
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


def _status_cell(script: dict) -> str:
    """状态三态：软删 → 已删除；enabled=false → 已停用；否则已启用。"""
    if script.get("deleted"):
        return "🗑️ 已删除"
    if not script.get("enabled", True):
        return "⏸️ 已停用"
    return "✅ 已启用"


def _source_cell(script: dict) -> str:
    """来源单元格：本仓库自写，或外部来源类型 + 原帖链接。"""
    url = script.get("source_url")
    if not url:
        return "自写（本仓库）"
    stype = escape_md_cell(script.get("source_type") or "外部来源")
    return f"{stype} · [来源页]({url})"


def build_issue_index(discussions: list) -> str:
    """版本帖索引表体：倒序累积，空列表返回占位行。"""
    if not discussions:
        return "| - | - | 暂无版本帖 |"
    rows = []
    for d in reversed(discussions):
        version = escape_md_cell(f"v{d['version']}" if d.get("version") else "-")
        rows.append(
            f"| {version} | {escape_md_cell(d.get('created_at') or '-')} "
            f"| [讨论 #{d['number']} →]({d['url']}) |"
        )
    return "\n".join(rows)


def tombstone_body(name: str, discussions: list | None = None) -> str:
    """墓碑正文：保留历史讨论的说明 + 历史版本帖回链（不携带 script-id 标记）。"""
    lines = [
        f"> ⚠️ 脚本 `{escape_md_cell(name)}` 已从仓库删除。"
        "本页保留历史讨论，不再更新。"
    ]
    if discussions:
        lines += ["", "**历史版本帖：**", ""]
        for d in reversed(discussions):
            tag = f"v{d['version']}" if d.get("version") else "-"
            lines.append(f"- [{tag} · #{d['number']}]({d['url']})")
    return "\n".join(lines) + "\n"


def build_issue_body(script: dict) -> str:
    """Issue 数据面板正文（活字段 + 版本帖索引），幂等可对账（D5）。"""
    sid = script["id"]
    name = escape_md_cell(script.get("name", sid))
    version = escape_md_cell(script.get("version") or "-")
    install_url = get_install_url(sid)

    lines = [
        build_marker(sid),
        "",
        f"## {name}",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 状态 | {_status_cell(script)} |",
        f"| 最新版本 | {version} |",
        f"| 名称 | {name} |",
        f"| 安装链接 | [安装脚本]({install_url}) |",
        f"| 来源 | {_source_cell(script)} |",
        "",
        "## 版本讨论帖",
        "",
        "每个版本一个讨论帖，按版本参与讨论：",
        "",
        "| 版本 | 日期 | 讨论 |",
        "| --- | --- | --- |",
        build_issue_index(script.get("discussions") or []),
        "",
    ]
    return "\n".join(lines)


def build_discussion_title(script: dict, today: str | None = None) -> str:
    """版本帖标题：`[vX.Y.Z] 名称 YYYY-MM-DD`；缺版本用 [初始版本]（D1）。"""
    day = today or date.today().isoformat()
    version = script.get("version")
    tag = f"v{version}" if version else "初始版本"
    return f"[{tag}] {script.get('name', script['id'])} {day}"


def build_discussion_body(script: dict, prev_version: str | None = None) -> str:
    """版本帖正文：全量快照 + 描述 + 本次更新 + 文档 + 更新历史 + 回链（D6）。

    prev_version 为 None 表示首帖（`首次发布`），否则渲染 `自 vX 更新至 vY`。
    """
    sid = script["id"]
    name = escape_md_cell(script.get("name", sid))
    version = script.get("version")
    tag = f"v{version}" if version else "初始版本"
    author = escape_md_cell(script.get("author") or "-")
    match_rules = ", ".join(
        f"`{escape_md_cell(m)}`" for m in script.get("match") or ["*://*/*"]
    )
    install_url = get_install_url(sid)

    note = next(
        (c.get("note", "") for c in (script.get("changelog") or [])
         if c.get("version") == (version or "")),
        "",
    )
    transition = (
        f"自 v{prev_version} 更新至 **{tag}**"
        if prev_version else f"首次发布 **{tag}**"
    )
    if note:
        transition += f"：{note}"

    lines = [
        f"## {name}",
        "",
        "| 字段 | 值 |",
        "| --- | --- |",
        f"| 名称 | {name} |",
        f"| 版本 | {escape_md_cell(version or '-')} |",
        f"| 作者 | {author} |",
        f"| 匹配规则 | {match_rules} |",
        f"| 安装链接 | [安装脚本]({install_url}) |",
        "",
    ]
    if script.get("description"):
        lines += ["## 描述", "", str(script["description"]), ""]
    lines += ["## 本次更新", "", transition, ""]
    lines += [
        "## 文档", "",
        script.get("documentation") or "_暂无文档_", "",
        "## 更新历史", "",
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

    backlinks = []
    issue = script.get("issue") or {}
    if issue.get("number"):
        backlinks.append(
            f"[Issue #{issue['number']}（状态与索引）]({issue.get('url', '')})"
        )
    backlinks.append(f"[脚本详情页]({get_pages_base_url()}/scripts/{sid}.html)")
    lines += ["", "---", "", " · ".join(backlinks), ""]
    return "\n".join(lines)
