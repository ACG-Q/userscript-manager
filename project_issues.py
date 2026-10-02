#!/usr/bin/env python3
"""把 registry.json 单向投影到仓库 Issues（幂等对账式）。"""
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests

from userscript_manager.discussions import create_discussion, resolve_qa_category
from userscript_manager.registry import load_registry, save_registry
from userscript_manager.issue_page import (
    build_discussion_body, build_discussion_title,
    build_issue_body, build_title, script_id_from_body,
    tombstone_body, tombstone_title,
)

GRAPHQL_URL = "https://api.github.com/graphql"
LABEL_NAME = "script"
LABEL_COLOR = "0E8A16"
LABEL_DESC = "自动投影的脚本独立页"

REPO_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    id
  }
}
"""

LABELS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    labels(first: 100, after: $cursor) {
      nodes { id name }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

LIST_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issues(first: 100, filterBy: {states: [OPEN, CLOSED]}, after: $cursor) {
      nodes { id number title body state url }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""

CREATE_LABEL_MUTATION = """
mutation($repositoryId: ID!, $name: String!, $color: String!, $description: String!) {
  createLabel(input: {repositoryId: $repositoryId, name: $name, color: $color, description: $description}) {
    label { id }
  }
}
"""

CREATE_MUTATION = """
mutation($repositoryId: ID!, $title: String!, $body: String!, $labelIds: [ID!]) {
  createIssue(input: {repositoryId: $repositoryId, title: $title, body: $body, labelIds: $labelIds}) {
    issue { id number url }
  }
}
"""

UPDATE_MUTATION = """
mutation($issueId: ID!, $title: String!, $body: String!) {
  updateIssue(input: {id: $issueId, title: $title, body: $body}) {
    issue { id number url }
  }
}
"""

CLOSE_MUTATION = """
mutation($issueId: ID!, $title: String!, $body: String!) {
  updateIssue(input: {id: $issueId, title: $title, body: $body, state: CLOSED}) {
    issue { id number url }
  }
}
"""

REOPEN_MUTATION = """
mutation($issueId: ID!, $title: String!, $body: String!) {
  updateIssue(input: {id: $issueId, title: $title, body: $body, state: OPEN}) {
    issue { id number url }
  }
}
"""


class GraphQLClient:
    """最小 GitHub GraphQL 客户端：POST + Bearer，次级限速自动等待。"""
    def __init__(self, token: str):
        self.token = token

    def execute(self, query: str, variables: dict | None = None) -> dict:
        """执行查询并返回 data；GraphQL 错误抛 RuntimeError。"""
        resp = requests.post(
            GRAPHQL_URL,
            json={"query": query, "variables": variables or {}},
            headers={
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "userscript-manager",
            },
            timeout=30,
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("errors"):
            raise RuntimeError(f"GraphQL 错误: {payload['errors']}")
        return payload["data"]


def list_all_labels(client, owner: str, name: str) -> list[dict]:
    """分页拉取仓库全部 label（首个页面仅 50/100 条时也可能漏掉 script 标签）。"""
    out: list[dict] = []
    cursor = None
    while True:
        data = client.execute(
            LABELS_QUERY, {"owner": owner, "name": name, "cursor": cursor}
        )
        conn = data["repository"]["labels"]
        out.extend(conn["nodes"])
        if not conn["pageInfo"]["hasNextPage"]:
            return out
        cursor = conn["pageInfo"]["endCursor"]


def ensure_label_id(client, repo_id: str, labels: list[dict]) -> str | None:
    """幂等取 script 标签 id；创建被拒时降级返回 None（不阻断投影）。"""
    for node in labels:
        if node["name"] == LABEL_NAME:
            return node["id"]
    try:
        created = client.execute(CREATE_LABEL_MUTATION, {
            "repositoryId": repo_id,
            "name": LABEL_NAME,
            "color": LABEL_COLOR,
            "description": LABEL_DESC,
        })
    except Exception as e:
        print(f"⚠️ 创建 label 失败，降级为无 label 创建：{e}", file=sys.stderr)
        return None
    return created["createLabel"]["label"]["id"]


def list_all_issues(client, owner: str, name: str) -> list[dict]:
    """分页拉取仓库全部 Issue（含已关闭），供投影器对账。"""
    out: list[dict] = []
    cursor = None
    while True:
        data = client.execute(LIST_QUERY, {"owner": owner, "name": name, "cursor": cursor})
        conn = data["repository"]["issues"]
        out.extend(conn["nodes"])
        if not conn["pageInfo"]["hasNextPage"]:
            return out
        cursor = conn["pageInfo"]["endCursor"]


def ensure_discussion_post(client, script: dict, repo_id: str,
                           owner: str, name: str, actions: list[str]) -> bool:
    """版本变化才发帖（账本幂等）；失败打日志不阻断，下轮对账自动补发。

    发帖成功返回 True（调用方据此标脏落盘）；幂等跳过或失败均返回 False。
    """
    ledger = script.setdefault("discussions", [])
    current = script.get("version")
    if ledger and ledger[-1].get("version") == current:
        return False
    prev = ledger[-1].get("version") if ledger else None
    try:
        category_id = resolve_qa_category(client, owner, name)
        created = create_discussion(
            client, repo_id, category_id,
            build_discussion_title(script),
            build_discussion_body(script, prev),
        )
    except Exception as e:
        print(f"⚠️ 版本帖创建失败（下轮对账自动补发）：{e}", file=sys.stderr)
        return False
    ledger.append({
        "version": current,
        "number": created["number"],
        "node_id": created["id"],
        "url": created["url"],
        "created_at": date.today().isoformat(),
    })
    actions.append(
        f"发布版本帖 v{current or '-'} → #{created['number']}："
        f"{script.get('name', script['id'])}"
    )
    return True


def project(client, registry: dict, owner: str, name: str) -> list[str]:
    """对账式投影：创建/更新/回填/墓碑化，返回人类可读的动作日志。

    受控例外：仅回写 script["issue"] 追踪字段后保存 registry。"""
    actions: list[str] = []
    repo = client.execute(REPO_QUERY, {"owner": owner, "name": name})["repository"]
    label_id = ensure_label_id(client, repo["id"], list_all_labels(client, owner, name))
    issues = list_all_issues(client, owner, name)

    by_marker: dict[str, dict] = {}
    by_number: dict[int, dict] = {}
    for d in issues:
        by_number[d["number"]] = d
        sid = script_id_from_body(d["body"])
        if sid:
            by_marker[sid] = d

    dirty = False
    for script in registry["scripts"]:
        tracking = script.get("issue") or {}
        target = None
        if tracking.get("node_id"):
            target = next((d for d in issues if d["id"] == tracking["node_id"]), None)
        if target is None and tracking.get("number"):
            target = by_number.get(tracking["number"])
        if target is None:
            target = by_marker.get(script["id"])

        label = script.get("name", script["id"])
        deleted = bool(script.get("deleted"))

        if target is None:
            if deleted:
                continue  # 未投影的软删脚本：不新建、不发帖
            created = client.execute(CREATE_MUTATION, {
                "repositoryId": repo["id"],
                "title": build_title(script),
                "body": build_issue_body(script),
                "labelIds": label_id,
            })["createIssue"]["issue"]
            script["issue"] = {"number": created["number"],
                               "node_id": created["id"], "url": created["url"]}
            tracking = script["issue"]  # 已写入追踪，跳过紧随的回填判断
            dirty = True
            actions.append(f"创建 Issue #{created['number']}：{label}")
            target = {"id": created["id"], "number": created["number"],
                      "url": created["url"], "title": build_title(script),
                      "body": build_issue_body(script), "state": "OPEN"}

        if deleted:
            expected_title = tombstone_title(build_title(script))
            expected_body = tombstone_body(script.get("name", script["id"]),
                                           script.get("discussions"))
            if (target["title"] != expected_title
                    or target["body"] != expected_body
                    or target.get("state") != "CLOSED"):
                client.execute(CLOSE_MUTATION, {
                    "issueId": target["id"],
                    "title": expected_title,
                    "body": expected_body,
                })
                actions.append(f"墓碑化已删除脚本 #{target['number']}：{label}")
        else:
            if ensure_discussion_post(client, script, repo["id"],
                                      owner, name, actions):
                dirty = True
            expected_title = build_title(script)
            expected_body = build_issue_body(script)
            if target.get("state") == "CLOSED":
                client.execute(REOPEN_MUTATION, {
                    "issueId": target["id"],
                    "title": expected_title,
                    "body": expected_body,
                })
                actions.append(f"重开 Issue #{target['number']}：{label}")
            elif (target["title"] != expected_title
                    or target["body"] != expected_body):
                client.execute(UPDATE_MUTATION, {
                    "issueId": target["id"],
                    "title": expected_title,
                    "body": expected_body,
                })
                actions.append(f"更新 Issue #{target['number']}：{label}")

        if (tracking.get("node_id") != target["id"]
                or tracking.get("number") != target["number"]
                or tracking.get("url") != target.get("url")):
            script["issue"] = {
                "number": target["number"],
                "node_id": target["id"],
                "url": target.get("url", ""),
            }
            dirty = True
            actions.append(f"回填 Issue 追踪字段：{label}")

    registry_ids = {s["id"] for s in registry["scripts"]}
    for sid, d in by_marker.items():
        if sid in registry_ids:
            continue
        name_hint = d["title"].removeprefix("📝 ").strip() or sid
        client.execute(CLOSE_MUTATION, {
            "issueId": d["id"],
            "title": tombstone_title(d["title"]),
            "body": tombstone_body(name_hint),
        })
        actions.append(f"墓碑化孤儿 Issue #{d['number']}：{name_hint}")

    if dirty:
        save_registry(registry)
    return actions


def main() -> int:
    """CLI 入口：按 registry 投影全部脚本 Issue 并输出动作摘要。"""
    token = os.getenv("GITHUB_TOKEN")
    repo_full = os.getenv("GITHUB_REPOSITORY", "")
    if not token or "/" not in repo_full:
        print("缺少 GITHUB_TOKEN 或 GITHUB_REPOSITORY，跳过 Issue 投影", file=sys.stderr)
        return 1
    owner, name = repo_full.split("/", 1)
    try:
        actions = project(GraphQLClient(token), load_registry(), owner, name)
    except Exception as e:
        print(f"Issue 投影失败：{e}", file=sys.stderr)
        return 1
    print("\n".join(actions) if actions else "Issue 投影：无需变更")
    return 0


if __name__ == "__main__":
    sys.exit(main())
