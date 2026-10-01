import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from userscript_manager.config import CONFIG
_tmp = Path(tempfile.mkdtemp(prefix="usm_proj_"))
CONFIG["registry_file"] = _tmp / "registry.json"
CONFIG["github_pages"]["base_url"] = ""
CONFIG["github_repo"] = "testuser/testrepo"

from userscript_manager.registry import load_registry, save_registry
from userscript_manager.issue_page import build_issue_body, build_marker, build_title
from project_discussions import project, list_all_discussions


def make_script(**overrides):
    script = {
        "id": "abc123", "type": "self", "name": "甲", "version": "1.0.0",
        "author": "作者", "match": ["*://a/*"], "documentation": "# 文档",
        "changelog": [{"version": "1.0.0", "date": "2026-10-01", "note": "初始版本"}],
    }
    script.update(overrides)
    return script


class FakeClient:
    def __init__(self, discussions=None, categories=None):
        self.discussions = [dict(d) for d in (discussions or [])]
        self.categories = categories or [{"id": "CAT_G", "name": "General"}]
        self.creates = []
        self.updates = []
        self._next_number = 100

    def execute(self, query, variables=None):
        variables = variables or {}
        if "discussionCategories" in query:
            return {"repository": {"id": "REPO_NODE",
                    "discussionCategories": {"nodes": list(self.categories)}}}
        if "discussions(first" in query:
            return {"repository": {"discussions": {
                "nodes": [dict(d) for d in self.discussions],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        if "createDiscussion" in query:
            self._next_number += 1
            created = {"id": f"D_new{self._next_number}", "number": self._next_number,
                       "url": f"https://github.com/o/r/discussions/{self._next_number}"}
            self.creates.append({"variables": variables, "result": created})
            return {"createDiscussion": {"discussion": created}}
        if "updateDiscussion" in query:
            self.updates.append(variables)
            return {"updateDiscussion": {"discussion": {"id": variables["discussionId"],
                    "number": 0, "url": ""}}}
        raise AssertionError(f"未知查询: {query!r}")


class TestProjector(unittest.TestCase):
    def setUp(self):
        self._saved = CONFIG["registry_file"]
        CONFIG["registry_file"] = _tmp / f"reg_{self.id()}.json"

    def tearDown(self):
        CONFIG["registry_file"] = self._saved

    def test_create_when_script_has_no_discussion(self):
        registry = {"scripts": [make_script()]}
        client = FakeClient()
        actions = project(client, registry, "o", "r")
        self.assertEqual(len(client.creates), 1)
        self.assertEqual(client.creates[0]["variables"]["categoryId"], "CAT_G")
        self.assertEqual(registry["scripts"][0]["discussion"]["number"], 101)
        self.assertEqual(load_registry()["scripts"][0]["discussion"]["node_id"], "D_new101")
        self.assertTrue(any("创建" in a for a in actions))

    def test_noop_when_body_already_in_sync(self):
        script = make_script(discussion={"number": 1, "node_id": "D_1", "url": "u1"})
        client = FakeClient(discussions=[{"id": "D_1", "number": 1,
            "title": build_title(script), "body": build_issue_body(script), "url": "u1"}])
        project(client, {"scripts": [script]}, "o", "r")
        self.assertEqual(client.creates, [])
        self.assertEqual(client.updates, [])

    def test_update_when_body_stale(self):
        script = make_script(discussion={"number": 1, "node_id": "D_1", "url": "u1"})
        client = FakeClient(discussions=[{"id": "D_1", "number": 1,
            "title": "旧标题", "body": "旧正文", "url": "u1"}])
        project(client, {"scripts": [script]}, "o", "r")
        self.assertEqual(len(client.updates), 1)
        self.assertEqual(client.updates[0]["discussionId"], "D_1")
        self.assertEqual(client.updates[0]["body"], build_issue_body(script))
        self.assertEqual(client.updates[0]["title"], build_title(script))

    def test_backfill_tracking_from_marker(self):
        script = make_script()
        stale_body = build_marker("abc123") + "\n旧内容"
        client = FakeClient(discussions=[{"id": "D_9", "number": 9,
            "title": build_title(script), "body": stale_body, "url": "u9"}])
        actions = project(client, {"scripts": [script]}, "o", "r")
        self.assertEqual(client.creates, [])
        self.assertEqual(script["discussion"]["node_id"], "D_9")
        self.assertTrue(any("回填" in a for a in actions))
        self.assertEqual(load_registry()["scripts"][0]["discussion"]["number"], 9)

    def test_orphan_tombstoned(self):
        registry = {"scripts": [make_script(id="kept")]}
        orphan_body = build_marker("gone") + "\n正文"
        client = FakeClient(discussions=[{"id": "D_5", "number": 5,
            "title": "📝 死脚本", "body": orphan_body, "url": "u5"}])
        actions = project(client, registry, "o", "r")
        self.assertEqual(len(client.updates), 1)
        self.assertTrue(client.updates[0]["title"].startswith("[已删除]"))
        self.assertNotIn("script-id", client.updates[0]["body"])
        self.assertTrue(any("墓碑" in a for a in actions))

    def test_create_uses_alternate_category_when_preferred_missing(self):
        registry = {"scripts": [make_script()]}
        client = FakeClient(categories=[{"id": "CAT_X", "name": "脚本"}])
        project(client, registry, "o", "r")
        self.assertEqual(client.creates[0]["variables"]["categoryId"], "CAT_X")


class PagedListClient:
    def __init__(self):
        self.calls = 0

    def execute(self, query, variables=None):
        variables = variables or {}
        self.calls += 1
        if not variables.get("cursor"):
            return {"repository": {"discussions": {
                "nodes": [{"id": "D1", "number": 1, "title": "t", "body": "b", "url": "u1"}],
                "pageInfo": {"hasNextPage": True, "endCursor": "CUR1"}}}}
        return {"repository": {"discussions": {
            "nodes": [{"id": "D2", "number": 2, "title": "t2", "body": "b2", "url": "u2"}],
            "pageInfo": {"hasNextPage": False, "endCursor": None}}}}


class TestListPagination(unittest.TestCase):
    def test_list_all_discussions_follows_cursor(self):
        client = PagedListClient()
        out = list_all_discussions(client, "o", "r")
        self.assertEqual([d["id"] for d in out], ["D1", "D2"])
        self.assertEqual(client.calls, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
