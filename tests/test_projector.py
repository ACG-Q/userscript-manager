import io
import os
import sys
import unittest
from contextlib import redirect_stderr

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from tests._helpers import ConfigIsolation
from userscript_manager.registry import load_registry
from userscript_manager.issue_page import build_issue_body, build_marker, build_title
from project_issues import project, list_all_issues


def make_script(**overrides):
    script = {
        "id": "abc123", "type": "self", "name": "甲", "version": "1.0.0",
        "author": "作者", "match": ["*://a/*"], "documentation": "# 文档",
        "changelog": [{"version": "1.0.0", "date": "2026-10-01", "note": "初始版本"}],
    }
    script.update(overrides)
    return script


class FakeClient:
    def __init__(self, issues=None, labels=None, fail_label=False):
        self.issues = [dict(d) for d in (issues or [])]
        self.labels = [dict(l) for l in (
            labels if labels is not None else [{"id": "LBL_script", "name": "script"}]
        )]
        self.fail_label = fail_label
        self.label_creates = []
        self.creates = []
        self.updates = []
        self.list_queries = []
        self._next_number = 100

    def execute(self, query, variables=None):
        variables = variables or {}
        if "labels(first" in query:
            return {"repository": {"id": "REPO_NODE",
                    "labels": {"nodes": [dict(l) for l in self.labels]}}}
        if "issues(first" in query:
            self.list_queries.append(query)
            return {"repository": {"issues": {
                "nodes": [dict(d) for d in self.issues],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        if "createLabel" in query:
            if self.fail_label:
                raise RuntimeError("FORBIDDEN: label 被拒")
            self.label_creates.append(variables)
            label = {"id": "LBL_new", "name": variables["name"]}
            self.labels.append(label)
            return {"createLabel": {"label": label}}
        if "createIssue" in query:
            self._next_number += 1
            created = {"id": f"I_new{self._next_number}",
                       "number": self._next_number,
                       "url": f"https://github.com/o/r/issues/{self._next_number}"}
            self.creates.append({"variables": variables, "result": created})
            return {"createIssue": {"issue": created}}
        if "updateIssue" in query:
            self.updates.append({"query": query, "variables": variables})
            return {"updateIssue": {"issue": {"id": variables["issueId"],
                    "number": 0, "url": ""}}}
        raise AssertionError(f"未知查询: {query!r}")


class TestProjector(ConfigIsolation):
    TMP_PREFIX = "usm_proj_"

    def test_create_when_script_has_no_issue(self):
        registry = {"scripts": [make_script()]}
        client = FakeClient()
        actions = project(client, registry, "o", "r")
        self.assertEqual(len(client.creates), 1)
        self.assertEqual(client.creates[0]["variables"]["labelIds"], "LBL_script")
        self.assertEqual(registry["scripts"][0]["issue"]["number"], 101)
        self.assertEqual(load_registry()["scripts"][0]["issue"]["node_id"], "I_new101")
        self.assertTrue(any("创建" in a for a in actions))

    def test_label_ensure_skips_when_present(self):
        client = FakeClient()
        project(client, {"scripts": [make_script()]}, "o", "r")
        self.assertEqual(client.label_creates, [])

    def test_label_created_when_missing(self):
        client = FakeClient(labels=[])
        project(client, {"scripts": [make_script()]}, "o", "r")
        self.assertEqual(len(client.label_creates), 1)
        self.assertEqual(client.label_creates[0]["name"], "script")
        self.assertEqual(client.creates[0]["variables"]["labelIds"], "LBL_new")

    def test_label_failure_degrades_to_unlabeled(self):
        client = FakeClient(labels=[], fail_label=True)
        err = io.StringIO()
        with redirect_stderr(err):
            actions = project(client, {"scripts": [make_script()]}, "o", "r")
        self.assertIsNone(client.creates[0]["variables"]["labelIds"])
        self.assertIn("降级", err.getvalue())
        self.assertTrue(any("创建" in a for a in actions))

    def test_noop_when_body_already_in_sync(self):
        script = make_script(issue={"number": 1, "node_id": "I_1", "url": "u1"})
        client = FakeClient(issues=[{"id": "I_1", "number": 1,
            "title": build_title(script), "body": build_issue_body(script),
            "url": "u1", "state": "OPEN"}])
        project(client, {"scripts": [script]}, "o", "r")
        self.assertEqual(client.creates, [])
        self.assertEqual(client.updates, [])

    def test_update_when_body_stale(self):
        script = make_script(issue={"number": 1, "node_id": "I_1", "url": "u1"})
        client = FakeClient(issues=[{"id": "I_1", "number": 1,
            "title": "旧标题", "body": "旧正文", "url": "u1", "state": "OPEN"}])
        project(client, {"scripts": [script]}, "o", "r")
        self.assertEqual(len(client.updates), 1)
        self.assertEqual(client.updates[0]["variables"]["issueId"], "I_1")
        self.assertEqual(client.updates[0]["variables"]["body"], build_issue_body(script))
        self.assertEqual(client.updates[0]["variables"]["title"], build_title(script))

    def test_backfill_tracking_from_marker(self):
        script = make_script()
        stale_body = build_marker("abc123") + "\n旧内容"
        client = FakeClient(issues=[{"id": "I_9", "number": 9,
            "title": build_title(script), "body": stale_body,
            "url": "u9", "state": "OPEN"}])
        actions = project(client, {"scripts": [script]}, "o", "r")
        self.assertEqual(client.creates, [])
        self.assertEqual(script["issue"]["node_id"], "I_9")
        self.assertTrue(any("回填" in a for a in actions))
        self.assertEqual(load_registry()["scripts"][0]["issue"]["number"], 9)

    def test_stale_node_id_falls_back_to_number_and_rebackfills(self):
        # GitHub 数据留存策略可能使 node_id 失效：必须回落 number 命中同一 Issue
        # 并把新 node_id 回写，而不是误判「无追踪」再新建一个 Issue。
        script = make_script(issue={"number": 7, "node_id": "I_deleted_forever",
                                    "url": "u7"})
        client = FakeClient(issues=[{"id": "I_7", "number": 7,
            "title": "旧标题", "body": "旧正文", "url": "u7", "state": "OPEN"}])
        actions = project(client, {"scripts": [script]}, "o", "r")
        self.assertEqual(client.creates, [])
        self.assertEqual(len(client.updates), 1)
        self.assertEqual(client.updates[0]["variables"]["issueId"], "I_7")
        self.assertEqual(script["issue"]["node_id"], "I_7")
        self.assertTrue(any("回填" in a for a in actions))

    def test_orphan_tombstoned_with_close(self):
        registry = {"scripts": [make_script(id="kept")]}
        orphan_body = build_marker("gone") + "\n正文"
        client = FakeClient(issues=[{"id": "I_5", "number": 5,
            "title": "📝 死脚本", "body": orphan_body,
            "url": "u5", "state": "OPEN"}])
        actions = project(client, registry, "o", "r")
        self.assertEqual(len(client.updates), 1)
        self.assertIn("state: CLOSED", client.updates[0]["query"])
        self.assertTrue(client.updates[0]["variables"]["title"].startswith("[已删除]"))
        self.assertNotIn("script-id", client.updates[0]["variables"]["body"])
        self.assertTrue(any("墓碑" in a for a in actions))

    def test_list_query_includes_closed_states(self):
        client = FakeClient()
        project(client, {"scripts": [make_script()]}, "o", "r")
        self.assertIn("states: [OPEN, CLOSED]", client.list_queries[0])


class PagedListClient:
    def __init__(self):
        self.calls = 0

    def execute(self, query, variables=None):
        variables = variables or {}
        self.calls += 1
        if not variables.get("cursor"):
            return {"repository": {"issues": {
                "nodes": [{"id": "I1", "number": 1, "title": "t",
                           "body": "b", "url": "u1"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "CUR1"}}}}
        return {"repository": {"issues": {
            "nodes": [{"id": "I2", "number": 2, "title": "t2",
                       "body": "b2", "url": "u2"}],
            "pageInfo": {"hasNextPage": False, "endCursor": None}}}}


class TestListPagination(unittest.TestCase):
    def test_list_all_issues_follows_cursor(self):
        client = PagedListClient()
        out = list_all_issues(client, "o", "r")
        self.assertEqual([d["id"] for d in out], ["I1", "I2"])
        self.assertEqual(client.calls, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
