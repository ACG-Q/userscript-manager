#!/usr/bin/env python3
"""构建时拉取脚本 Issue 统计（回复数/已解决/最近 2 条回复），失败降级返回 None。"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

log = logging.getLogger(__name__)

_OWNER_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

_FIELDS = """
number
url
state
comments(last: 2) {
  totalCount
  nodes {
    author { login }
    authorAssociation
    body
    createdAt
  }
}
"""


@dataclass(frozen=True)
class LatestReply:
    """讨论区最近一条回复的摘要（作者/正文/时间/是否仓库成员）。"""
    author: str
    body: str
    created_at: str
    is_owner: bool


@dataclass(frozen=True)
class IssueStats:
    """单个脚本 Issue 的统计：回复数、关闭状态与最近 2 条回复。"""
    number: int
    url: str
    is_closed: bool
    reply_count: int
    replies: tuple[LatestReply, ...]  # 最近最多 2 条，按时间旧→新


def build_query(target_count: int) -> str:
    """生成带 d0..dN 别名的批量查询，一次请求取回全部讨论统计。"""
    args = ", ".join(f"$n{i}: Int!" for i in range(target_count))
    fields = "\n".join(
        f"d{i}: issue(number: $n{i}) {{ {_FIELDS} }}"
        for i in range(target_count)
    )
    return (
        f"query($owner: String!, $name: String!, {args}) {{ "
        f"repository(owner: $owner, name: $name) {{ {fields} }} }}"
    )


def clip(text: str, limit: int) -> str:
    """折叠空白并按字符数截断，超出以省略号结尾。"""
    collapsed = " ".join((text or "").split())
    return collapsed if len(collapsed) <= limit else collapsed[:limit] + "…"


def relative_time(iso: str, now: datetime | None = None) -> str:
    """把 ISO 时间戳转为构建时刻的中文相对时间；空串/非法值返回占位符。"""
    if not iso:
        return "—"
    now = now or datetime.now(timezone.utc)
    try:
        created = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return "—"
    seconds = (now - created).total_seconds()
    if seconds < 60:
        return "刚刚"
    if seconds < 3600:
        return f"{int(seconds // 60)} 分钟前"
    if seconds < 86400:
        return f"{int(seconds // 3600)} 小时前"
    days = int(seconds // 86400)
    if days < 30:
        return f"{days} 天前"
    return created.strftime("%Y-%m-%d")


def fetch_stats(
    client, owner: str, name: str, scripts: list[dict]
) -> dict[str, IssueStats] | None:
    """按脚本 id 返回讨论统计字典。

    无 Issue 的脚本不占位；整体请求失败返回 None（触发站点降级渲染）。"""
    targets: list[tuple[str, int]] = []
    for s in scripts:
        number = (s.get("issue") or {}).get("number")
        if number:
            targets.append((s["id"], number))
    if not targets:
        return {}
    variables: dict = {"owner": owner, "name": name}
    for i, (_sid, number) in enumerate(targets):
        variables[f"n{i}"] = number
    try:
        data = client.execute(build_query(len(targets)), variables)
    except Exception as e:
        log.warning("讨论统计拉取失败，站点降级渲染：%s", e, exc_info=True)
        return None
    repository = (data or {}).get("repository") or {}
    stats: dict[str, IssueStats] = {}
    for i, (sid, _number) in enumerate(targets):
        node = repository.get(f"d{i}")
        if not node:
            continue
        comments = node.get("comments") or {}
        nodes = comments.get("nodes") or []
        replies = []
        for raw in nodes:
            login = ((raw.get("author") or {}).get("login")) or "未知用户"
            replies.append(LatestReply(
                author=login,
                body=raw.get("body") or "",
                created_at=raw.get("createdAt") or "",
                is_owner=raw.get("authorAssociation") in _OWNER_ASSOCIATIONS,
            ))
        stats[sid] = IssueStats(
            number=node.get("number") or 0,
            url=node.get("url") or "",
            is_closed=(node.get("state") == "CLOSED"),
            reply_count=comments.get("totalCount") or 0,
            replies=tuple(replies),
        )
    return stats
