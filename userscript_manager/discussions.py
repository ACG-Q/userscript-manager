"""GitHub Discussions 能力层：Q&A 分类解析、发帖、按帖拉取评论。

client 为鸭子类型（只需 .execute(query, variables)），不反向依赖根目录投影器。
"""

from __future__ import annotations

from typing import Any

from .issue_stats import OWNER_ASSOCIATIONS

CATEGORY_PAGE_SIZE = 100

DISCUSSION_CATEGORIES_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    discussionCategories(first: %d, after: $cursor) {
      nodes { id name }
      pageInfo { hasNextPage endCursor }
    }
  }
}
""" % CATEGORY_PAGE_SIZE

CREATE_DISCUSSION_MUTATION = """
mutation($repositoryId: ID!, $categoryId: ID!, $title: String!, $body: String!) {
  createDiscussion(input: {repositoryId: $repositoryId, categoryId: $categoryId,
                           title: $title, body: $body}) {
    discussion { id number url }
  }
}
"""

# 顶层 Query 上没有 discussion(id:) 字段（线上报 undefinedField），
# 只能走通用 node(id) 查询，再用内联片段收窄到 Discussion。
DISCUSSION_NODE_QUERY = """
query($id: ID!) {
  node(id: $id) {
    ... on Discussion {
      title
      url
      isAnswered
      comments(first: 100) {
        totalCount
        nodes {
          author { login }
          authorAssociation
          body
          createdAt
          isAnswer
          replies(first: 50) {
            totalCount
            nodes { author { login } authorAssociation body createdAt isAnswer }
          }
        }
      }
    }
  }
}
"""

_CATEGORY_CACHE: dict[str, str] = {}


def resolve_qa_category(client: Any, owner: str, name: str) -> str:
    """解析仓库 Q&A 讨论分类 id（进程内缓存，缺分类抛带指引的 RuntimeError）。"""
    key = f"{owner}/{name}"
    if key in _CATEGORY_CACHE:
        return _CATEGORY_CACHE[key]
    cursor = None
    while True:
        data = client.execute(DISCUSSION_CATEGORIES_QUERY,
                              {"owner": owner, "name": name, "cursor": cursor})
        container = ((data or {}).get("repository") or {}).get("discussionCategories") or {}
        for node in container.get("nodes") or []:
            if (node.get("name") or "").strip().lower() == "q&a":
                _CATEGORY_CACHE[key] = node["id"]
                return str(node["id"])
        page = container.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not cursor:
            break
    raise RuntimeError(
        "仓库未启用 Q&A 讨论分类：请在 Settings → Discussions → Categories "
        "启用/新建名为 Q&A 的分类后重试。"
    )


def create_discussion(client: Any, repository_id: str, category_id: str,
                      title: str, body: str) -> dict[str, Any]:
    """创建讨论帖，返回 {id, number, url}。"""
    data = client.execute(CREATE_DISCUSSION_MUTATION, {
        "repositoryId": repository_id,
        "categoryId": category_id,
        "title": title,
        "body": body,
    })
    created: dict[str, Any] = data["createDiscussion"]["discussion"]
    return created


def _normalize_comment(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "author": ((raw.get("author") or {}).get("login")) or "未知用户",
        "is_owner": raw.get("authorAssociation") in OWNER_ASSOCIATIONS,
        "body": raw.get("body") or "",
        "created_at": raw.get("createdAt") or "",
        "is_answer": bool(raw.get("isAnswer")),
        "replies": [_normalize_comment(r) for r in ((raw.get("replies") or {}).get("nodes") or [])],
    }


def fetch_discussion_comments(client: Any, node_id: str) -> dict[str, Any] | None:
    """按 node_id 拉取单帖：{title, url, is_answered, comments:[...]}。

    帖不存在、无读取权限、或节点不是 Discussion（内联片段未命中）时返回 None。
    评论取前 100/回复前 50（GraphQL connection 上限），超出以 comment_total 检测截断。"""
    data = client.execute(DISCUSSION_NODE_QUERY, {"id": node_id})
    node = (data or {}).get("node") or {}
    if "comments" not in node:
        return None
    comments = node.get("comments") or {}
    return {
        "title": node.get("title") or "",
        "url": node.get("url") or "",
        "is_answered": bool(node.get("isAnswered")),
        "comment_total": comments.get("totalCount") or 0,
        "comments": [_normalize_comment(c) for c in (comments.get("nodes") or [])],
    }
