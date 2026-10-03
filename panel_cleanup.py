#!/usr/bin/env python3
"""命令面板（Issue #1）定期清理：保留最近 KEEP_GROUPS 组，其余归档到仓库后删除。

一条「组」= 一条以 ``/`` 开头的命令评论 + 其后的执行结果评论（直到下一条命令）。

安全约定：
- 先拉全部评论，拉取失败直接退出且不改动任何数据；
- 先写归档（按评论 id 幂等，重复执行不会重复归档）再删除，删除失败下次只补删除；
- 归档成功即返回 0，交由 workflow 提交，避免「已删未存」的数据丢失。
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from userscript_manager.config import CONFIG

KEEP_GROUPS = 10  # Issue #1 上保留的「命令 + 结果」组数
COMMAND_PREFIX = "/"  # 命令评论的判定前缀

PANEL_QUERY = """
query($owner: String!, $name: String!, $number: Int!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    issue(number: $number) {
      comments(first: 100, after: $cursor) {
        totalCount
        nodes {
          id
          author { login }
          authorAssociation
          body
          createdAt
        }
        pageInfo { hasNextPage endCursor }
      }
    }
  }
}
"""

DELETE_COMMENT_MUTATION = """
mutation($id: ID!) {
  deleteIssueComment(input: {id: $id}) { clientMutationId }
}
"""


def fetch_panel_comments(client, owner: str, name: str, number: int) -> list[dict]:
    """分页拉取命令面板全部评论，按时间旧→新返回规范化列表。"""
    comments: list[dict] = []
    cursor = None
    while True:
        data = client.execute(PANEL_QUERY, {
            "owner": owner, "name": name, "number": number, "cursor": cursor,
        })
        issue = ((data or {}).get("repository") or {}).get("issue") or {}
        conn = issue.get("comments") or {}
        for node in conn.get("nodes") or []:
            comments.append({
                "id": node.get("id") or "",
                "author": ((node.get("author") or {}).get("login")) or "未知用户",
                "association": node.get("authorAssociation") or "",
                "body": node.get("body") or "",
                "created_at": node.get("createdAt") or "",
            })
        page = conn.get("pageInfo") or {}
        if not page.get("hasNextPage"):
            break
        cursor = page.get("endCursor")
        if not cursor:
            break
    return comments


def is_command(comment: dict) -> bool:
    """命令评论：正文（去空白）以 ``/`` 开头。"""
    return (comment.get("body") or "").lstrip().startswith(COMMAND_PREFIX)


def group_commands(comments: list[dict]) -> list[dict]:
    """把每条命令与其后的结果评论配成一组；命令之前的孤儿评论自成一组。"""
    groups: list[dict] = []
    current: dict | None = None
    for c in comments:
        if is_command(c):
            current = {"command": c, "results": []}
            groups.append(current)
        elif current is None:
            current = {"command": None, "results": [c]}
            groups.append(current)
        else:
            current["results"].append(c)
    return groups


def group_ids(group: dict) -> list[str]:
    """一组内需要归档/删除的全部评论 id（命令 + 结果）。"""
    ids = []
    cmd = group.get("command")
    if cmd and cmd.get("id"):
        ids.append(cmd["id"])
    ids += [r["id"] for r in group.get("results") or [] if r.get("id")]
    return ids


def _entry_key(entry: dict) -> str:
    """归档条目的主键：命令评论 id，孤儿组退化为首条结果 id。"""
    return entry.get("command_id") or (
        (entry.get("results") or [{}])[0].get("id") or ""
    )


def archive_entry(group: dict, now: str | None = None) -> dict:
    """一组 → 归档条目（命令正文 + 其全部结果）。"""
    cmd = group.get("command")
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "command_id": (cmd or {}).get("id") or "",
        "author": (cmd or {}).get("author") or "",
        "command": (cmd or {}).get("body") or "",
        "created_at": (cmd or {}).get("created_at") or "",
        "results": [
            {"id": r.get("id") or "", "author": r.get("author") or "",
             "body": r.get("body") or "", "created_at": r.get("created_at") or ""}
            for r in group.get("results") or []
        ],
        "archived_at": now,
    }


def load_archive(path: Path) -> dict:
    """读归档账本；缺失/损坏时返回空账本（不抛错，避免阻断清理）。"""
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("commands"), list):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    return {"schema": 1, "commands": []}


def save_archive(path: Path, archive: dict) -> None:
    """原子写归档账本（临时文件 + replace）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, path)


def merge_archive(archive: dict, groups: list[dict]) -> bool:
    """把待清理组并入归档，按评论 id 幂等；返回账本是否有变化。"""
    changed = False
    known = set()
    for entry in archive["commands"]:
        if _entry_key(entry):
            known.add(_entry_key(entry))
        known.update(r.get("id") for r in entry.get("results") or [] if r.get("id"))
    for group in groups:
        ids = set(group_ids(group))
        if ids & known:
            # 已归档过的组：只补上还没进去的结果（上次删除失败的情况）
            existing = next(
                (e for e in archive["commands"]
                 if _entry_key(e) and _entry_key(e) in ids), None)
            if existing is None:
                continue
            have = {r.get("id") for r in existing.get("results") or []}
            for r in archive_entry(group)["results"]:
                if r["id"] and r["id"] not in have:
                    existing.setdefault("results", []).append(r)
                    changed = True
            continue
        archive["commands"].append(archive_entry(group))
        known |= ids
        changed = True
    return changed


def process(client, owner: str, name: str, number: int,
            keep: int = KEEP_GROUPS) -> list[str]:
    """拉取 → 分组 → 保留 keep 组 → 其余归档后删除，返回动作日志。"""
    comments = fetch_panel_comments(client, owner, name, number)
    groups = group_commands(comments)
    doomed = groups[:-keep] if len(groups) > keep else []
    if not doomed:
        return [f"命令面板无需清理：共 {len(groups)} 组，保留 {keep} 组"]

    actions = [f"命令面板共 {len(groups)} 组，清理 {len(doomed)} 组（保留最近 {keep} 组）"]
    archive = load_archive(CONFIG["archive_file"])
    if merge_archive(archive, doomed):
        save_archive(CONFIG["archive_file"], archive)
        actions.append(f"归档 {len(doomed)} 组 → {CONFIG['archive_file']}")

    deleted = failed = 0
    for group in doomed:  # 归档已落盘，删除失败不影响数据安全
        for cid in group_ids(group):
            try:
                client.execute(DELETE_COMMENT_MUTATION, {"id": cid})
                deleted += 1
            except Exception as e:
                failed += 1
                actions.append(f"删除失败 {cid}（下次重试）：{e}")
    actions.append(f"已删除 {deleted} 条评论" + (f"，失败 {failed} 条" if failed else ""))
    return actions


def main() -> int:
    """CLI 入口：清理命令面板并输出动作摘要；缺 token/仓库直接退出。"""
    token = os.getenv("GITHUB_TOKEN", "")
    repo = os.getenv("GITHUB_REPOSITORY", "")
    if not token or "/" not in repo:
        print("缺少 GITHUB_TOKEN 或 GITHUB_REPOSITORY，跳过命令面板清理",
              file=sys.stderr)
        return 1
    owner, name = repo.split("/", 1)
    from project_issues import GraphQLClient  # 复用仓库现有 GraphQL 客户端

    try:
        actions = process(GraphQLClient(token), owner, name,
                          CONFIG["control_issue_number"])
    except Exception as e:
        # 拉取阶段失败：归档与删除都还没发生，安全退出等下轮
        print(f"命令面板清理失败（未做任何改动）：{e}", file=sys.stderr)
        return 1
    print("\n".join(actions))
    return 0


if __name__ == "__main__":
    sys.exit(main())
