"""panel_cleanup.py 单元测试：配对、保留阈值、归档幂等与删除重试。"""

import contextlib
import io
import os
import unittest
from pathlib import Path

from tests._helpers import ConfigIsolation
from userscript_manager.config import CONFIG
from panel_cleanup import (
    fetch_panel_comments,
    group_commands,
    group_ids,
    load_archive,
    merge_archive,
    process,
)


def comment(body, cid, author="ACG-Q"):
    """面板评论的规范化结构（process 内部使用）。"""
    return {"id": cid, "author": author, "association": "OWNER",
            "body": body, "created_at": "2026-10-02T00:00:00Z"}


def node(body, cid, author="ACG-Q"):
    """GraphQL 原始节点结构（fetch_panel_comments 输入）。"""
    return {"id": cid, "author": {"login": author},
            "authorAssociation": "OWNER" if author == "ACG-Q" else "CONTRIBUTOR",
            "body": body, "createdAt": "2026-10-02T00:00:00Z"}


def panel_nodes(pairs):
    """[(命令, 结果), ...] → 交错的评论节点（命令在前、旧→新）。"""
    nodes, n = [], 0
    for command, result in pairs:
        n += 1
        nodes.append(node(command, f"IC_{n}"))
        n += 1
        nodes.append(node(result, f"IR_{n}", author="github-actions[bot]"))
    return nodes


class FakeClient:
    """返回固定评论列表并记录删除操作的 GraphQL 替身。"""

    def __init__(self, nodes, fail_delete=False):
        self.nodes = nodes
        self.fail_delete = fail_delete
        self.deleted = []

    def execute(self, query, variables=None):
        variables = variables or {}
        if "deleteIssueComment" in query:
            if self.fail_delete:
                raise RuntimeError("boom")
            self.deleted.append(variables["id"])
            return {"deleteIssueComment": {"clientMutationId": None}}
        return {"repository": {"issue": {"comments": {
            "totalCount": len(self.nodes),
            "nodes": self.nodes,
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }}}}


class TestGrouping(unittest.TestCase):
    def test_pairs_command_with_following_result(self):
        groups = group_commands([
            comment("/add x", "1"),
            comment("**执行结果：** ok", "2", author="github-actions[bot]"),
            comment("/list", "3"),
        ])
        self.assertEqual(len(groups), 2)
        self.assertEqual(groups[0]["command"]["id"], "1")
        self.assertEqual([r["id"] for r in groups[0]["results"]], ["2"])
        self.assertEqual(groups[1]["command"]["id"], "3")
        self.assertEqual(groups[1]["results"], [])

    def test_orphan_comment_forms_its_own_group(self):
        groups = group_commands([comment("随便聊聊", "1")])
        self.assertEqual(len(groups), 1)
        self.assertIsNone(groups[0]["command"])
        self.assertEqual(len(groups[0]["results"]), 1)

    def test_non_slash_body_is_not_a_command(self):
        self.assertFalse(group_commands([comment("谢谢！", "1")])[0]["command"])
        self.assertTrue(group_commands([comment("  /up 1", "1")])[0]["command"])

    def test_group_ids_covers_command_and_results(self):
        groups = group_commands([comment("/a", "IC_1"),
                                 comment("ok", "IR_2")])
        self.assertEqual(group_ids(groups[0]), ["IC_1", "IR_2"])


class TestFetchComments(unittest.TestCase):
    def test_paginates_until_done(self):
        class Paged:
            def __init__(self):
                self.calls = 0

            def execute(self, query, variables=None):
                self.calls += 1
                if self.calls == 1:
                    return {"repository": {"issue": {"comments": {
                        "totalCount": 2, "nodes": [node("/a", "IC_1")],
                        "pageInfo": {"hasNextPage": True, "endCursor": "CUR"},
                    }}}}
                return {"repository": {"issue": {"comments": {
                    "totalCount": 2, "nodes": [node("/b", "IC_2")],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                }}}}

        client = Paged()
        comments = fetch_panel_comments(client, "u", "r", 1)
        self.assertEqual([c["id"] for c in comments], ["IC_1", "IC_2"])
        self.assertEqual(client.calls, 2)
        self.assertEqual(comments[0]["author"], "ACG-Q")


class TestArchiveIdempotency(ConfigIsolation):
    """归档合并幂等；继承 ConfigIsolation 以免写到仓库真实 archive/ 路径。"""

    def test_merge_skips_already_archived_groups(self):
        archive = {"schema": 1, "commands": []}
        groups = group_commands([comment("/add x", "IC_1"),
                                 comment("ok", "IR_2")])
        self.assertTrue(merge_archive(archive, groups))
        self.assertEqual(len(archive["commands"]), 1)
        # 重复触发（删除失败后的第二轮）不得重复归档
        self.assertFalse(merge_archive(archive, groups))
        self.assertEqual(len(archive["commands"]), 1)

    def test_merge_backfills_results_missing_from_partial_archive(self):
        groups = group_commands([comment("/add x", "IC_1"),
                                 comment("ok", "IR_2")])
        archive = {"schema": 1, "commands": []}
        # 上一轮只归档了命令（结果删除失败）
        merge_archive(archive, [{"command": groups[0]["command"], "results": []}])
        self.assertEqual(archive["commands"][0]["results"], [])
        self.assertTrue(merge_archive(archive, groups))
        self.assertEqual(len(archive["commands"]), 1)
        self.assertEqual(len(archive["commands"][0]["results"]), 1)

    def test_load_archive_tolerates_missing_or_broken_file(self):
        missing = Path(CONFIG["archive_file"])
        self.assertEqual(load_archive(missing)["commands"], [])
        missing.parent.mkdir(parents=True, exist_ok=True)
        missing.write_text("{broken", encoding="utf-8")
        self.assertEqual(load_archive(missing)["commands"], [])


class TestProcess(ConfigIsolation):
    def test_keeps_last_groups_and_deletes_older(self):
        pairs = [(f"/cmd {i}", f"ok {i}") for i in range(1, 13)]  # 12 组
        client = FakeClient(panel_nodes(pairs))
        actions = process(client, "u", "r", 1, keep=10)
        # 2 组 ×（命令 + 结果）= 4 条被删
        self.assertEqual(len(client.deleted), 4)
        archive = load_archive(CONFIG["archive_file"])
        self.assertEqual(len(archive["commands"]), 2)
        self.assertEqual(archive["commands"][0]["command"], "/cmd 1")
        self.assertEqual(archive["commands"][1]["command"], "/cmd 2")
        self.assertTrue(any("清理 2 组" in a for a in actions))

    def test_within_keep_threshold_touches_nothing(self):
        client = FakeClient(panel_nodes([("/a", "ok")]))
        actions = process(client, "u", "r", 1, keep=10)
        self.assertEqual(client.deleted, [])
        self.assertFalse(Path(CONFIG["archive_file"]).exists())
        self.assertTrue(any("无需清理" in a for a in actions))

    def test_rerun_after_delete_failure_does_not_duplicate(self):
        nodes = panel_nodes([(f"/cmd {i}", f"ok {i}") for i in range(1, 13)])
        failing = FakeClient(nodes, fail_delete=True)
        process(failing, "u", "r", 1, keep=10)
        self.assertEqual(failing.deleted, [])
        archive = load_archive(CONFIG["archive_file"])
        self.assertEqual(len(archive["commands"]), 2)   # 归档已先落盘

        retry = FakeClient(nodes)
        process(retry, "u", "r", 1, keep=10)
        archive = load_archive(CONFIG["archive_file"])
        self.assertEqual(len(archive["commands"]), 2)   # 没有重复归档
        self.assertEqual(len(retry.deleted), 4)         # 只补删除


class TestMainEntry(ConfigIsolation):
    def test_main_without_token_exits_nonzero(self):
        import panel_cleanup as pc
        orig = os.environ.pop("GITHUB_TOKEN", None)
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                rc = pc.main()
        finally:
            if orig is not None:
                os.environ["GITHUB_TOKEN"] = orig
        self.assertEqual(rc, 1)
        self.assertIn("GITHUB_TOKEN", err.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
