#!/usr/bin/env python3
"""把 registry.json 单向投影到仓库 Issues（幂等对账式）。"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import requests

from userscript_manager.registry import load_registry, save_registry
from userscript_manager.issue_page import (
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
    labels(first: 50) { nodes { id name } }
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


class GraphQLClient:
    def __init__(self, token: str):
        self.token = token

    def execute(self, query: str, variables: dict | None = None) -> dict:
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


def ensure_label_id(client, repo: dict) -> str | None:
    """幂等取 script 标签 id；创建被拒时降级返回 None（不阻断投影）。"""
    for node in repo["labels"]["nodes"]:
        if node["name"] == LABEL_NAME:
            return node["id"]
    try:
        created = client.execute(CREATE_LABEL_MUTATION, {
            "repositoryId": repo["id"],
            "name": LABEL_NAME,
            "color": LABEL_COLOR,
            "description": LABEL_DESC,
        })
    except Exception as e:
        print(f"⚠️ 创建 label 失败，降级为无 label 创建：{e}", file=sys.stderr)
        return None
    return created["createLabel"]["label"]["id"]


def list_all_issues(client, owner: str, name: str) -> list[dict]:
    out: list[dict] = []
    cursor = None
    while True:
        data = client.execute(LIST_QUERY, {"owner": owner, "name": name, "cursor": cursor})
        conn = data["repository"]["issues"]
        out.extend(conn["nodes"])
        if not conn["pageInfo"]["hasNextPage"]:
            return out
        cursor = conn["pageInfo"]["endCursor"]


def project(client, registry: dict, owner: str, name: str) -> list[str]:
    """对账式投影：创建/更新/回填/墓碑化，返回人类可读的动作日志。

    受控例外：仅回写 script["issue"] 追踪字段后保存 registry。"""
    actions: list[str] = []
    repo = client.execute(REPO_QUERY, {"owner": owner, "name": name})["repository"]
    label_id = ensure_label_id(client, repo)
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
        if target is None:
            created = client.execute(CREATE_MUTATION, {
                "repositoryId": repo["id"],
                "title": build_title(script),
                "body": build_issue_body(script),
                "labelIds": label_id,
            })["createIssue"]["issue"]
            script["issue"] = {"number": created["number"],
                               "node_id": created["id"], "url": created["url"]}
            dirty = True
            actions.append(f"创建 Issue #{created['number']}：{label}")
            continue

        expected_title = build_title(script)
        expected_body = build_issue_body(script)
        if target["title"] != expected_title or target["body"] != expected_body:
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
