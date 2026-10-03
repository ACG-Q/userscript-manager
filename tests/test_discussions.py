"""discussions.py 能力层单元测试。"""

import unittest

from userscript_manager.discussions import (
    create_discussion,
    fetch_discussion_comments,
    resolve_qa_category,
)


class FakeClient:
    """按查询片段路由的 GraphQL 测试替身。"""

    def __init__(self, categories=None, fail=False):
        self.categories = categories if categories is not None else [
            {"id": "CAT_general", "name": "General"},
            {"id": "CAT_qa", "name": "Q&A"},
        ]
        self.fail = fail
        self.calls = []
        self.created = []

    def execute(self, query, variables=None):
        variables = variables or {}
        self.calls.append((query, variables))
        if self.fail:
            raise RuntimeError("network down")
        if "discussionCategories" in query:
            return {"repository": {"discussionCategories": {
                "nodes": [dict(c) for c in self.categories],
                "pageInfo": {"hasNextPage": False, "endCursor": None}}}}
        if "createDiscussion" in query:
            self._n = getattr(self, "_n", 6) + 1
            d = {"id": f"D_{self._n}", "number": self._n,
                 "url": f"https://github.com/u/r/discussions/{self._n}"}
            self.created.append({"variables": variables, "result": d})
            return {"createDiscussion": {"discussion": d}}
        if "node(id" in query:
            return {"node": {
                "title": "帖子", "url": "https://github.com/u/r/discussions/7",
                "isAnswered": True,
                "comments": {"totalCount": 2, "nodes": [
                    {"author": {"login": "访客"}, "authorAssociation": "NONE",
                     "body": "问题", "createdAt": "2026-10-01T00:00:00Z", "isAnswer": False,
                     "replies": {"totalCount": 1, "nodes": [
                         {"author": {"login": "作者"}, "authorAssociation": "OWNER",
                          "body": "回复", "createdAt": "2026-10-01T01:00:00Z",
                          "isAnswer": True}]}},
                    {"author": None, "authorAssociation": "NONE",
                     "body": "匿名", "createdAt": "2026-10-02T00:00:00Z",
                     "isAnswer": False},
                ]}}}
        raise AssertionError(f"未知查询: {query!r}")


def setUpModule():
    # 清进程内缓存，避免用例间串扰
    from userscript_manager import discussions
    discussions._CATEGORY_CACHE.clear()


class TestResolveQaCategory(unittest.TestCase):
    def test_resolves_case_insensitive(self):
        from userscript_manager import discussions
        discussions._CATEGORY_CACHE.clear()
        client = FakeClient()
        cid = resolve_qa_category(client, "u", "r")
        self.assertEqual(cid, "CAT_qa")

    def test_cached_across_calls(self):
        from userscript_manager import discussions
        discussions._CATEGORY_CACHE.clear()
        client = FakeClient()
        resolve_qa_category(client, "u", "r")
        n = len(client.calls)
        resolve_qa_category(client, "u", "r")
        self.assertEqual(len(client.calls), n)

    def test_missing_qa_raises_with_hint(self):
        from userscript_manager import discussions
        discussions._CATEGORY_CACHE.clear()
        client = FakeClient(categories=[{"id": "C1", "name": "General"}])
        with self.assertRaises(RuntimeError) as ctx:
            resolve_qa_category(client, "u", "r")
        self.assertIn("Settings → Discussions → Categories", str(ctx.exception))

    def test_paginates_until_qa_found(self):
        from userscript_manager import discussions
        discussions._CATEGORY_CACHE.clear()

        class PagedClient:
            """首页无 Q&A（有游标），次页含小写 q&a。"""

            def __init__(self):
                self.calls = []

            def execute(self, query, variables=None):
                variables = variables or {}
                self.calls.append(variables)
                if not variables.get("cursor"):
                    nodes = [{"id": "C1", "name": "General"}]
                    page = {"hasNextPage": True, "endCursor": "CUR1"}
                else:
                    nodes = [{"id": "C2", "name": "q&a"}]
                    page = {"hasNextPage": False, "endCursor": None}
                return {"repository": {"discussionCategories": {
                    "nodes": nodes, "pageInfo": page}}}

        client = PagedClient()
        cid = resolve_qa_category(client, "u", "r")
        self.assertEqual(cid, "C2")
        self.assertEqual(len(client.calls), 2)
        self.assertIsNone(client.calls[0].get("cursor"))
        self.assertEqual(client.calls[1].get("cursor"), "CUR1")

    def test_stops_when_next_page_cursor_missing(self):
        from userscript_manager import discussions
        discussions._CATEGORY_CACHE.clear()

        class EndlessClient:
            """恒返回 hasNextPage=True 但 endCursor=None；超限哨兵防挂死。"""

            def __init__(self):
                self.calls = []

            def execute(self, query, variables=None):
                self.calls.append((query, variables or {}))
                if len(self.calls) > 10:
                    raise RuntimeError("call cap exceeded: cursor never advanced")
                return {"repository": {"discussionCategories": {
                    "nodes": [{"id": "C1", "name": "General"}],
                    "pageInfo": {"hasNextPage": True, "endCursor": None}}}}

        client = EndlessClient()
        with self.assertRaises(RuntimeError) as ctx:
            resolve_qa_category(client, "u", "r")
        self.assertIn("Settings → Discussions → Categories", str(ctx.exception))
        self.assertLessEqual(len(client.calls), 3)


class TestCreateAndFetch(unittest.TestCase):
    def test_create_discussion_returns_node(self):
        client = FakeClient()
        d = create_discussion(client, "REPO_NODE", "CAT_qa", "[v1.0.0] 甲 2026-10-02", "正文")
        self.assertEqual(d["number"], 7)
        self.assertEqual(d["url"], "https://github.com/u/r/discussions/7")
        self.assertEqual(client.created[0]["variables"]["categoryId"], "CAT_qa")
        self.assertEqual(client.created[0]["variables"]["title"], "[v1.0.0] 甲 2026-10-02")
        self.assertEqual(client.created[0]["variables"]["repositoryId"], "REPO_NODE")
        self.assertEqual(client.created[0]["variables"]["body"], "正文")

    def test_client_failure_propagates(self):
        from userscript_manager import discussions
        discussions._CATEGORY_CACHE.clear()
        with self.assertRaises(RuntimeError) as ctx:
            resolve_qa_category(FakeClient(fail=True), "u", "r")
        self.assertIn("network down", str(ctx.exception))

    def test_fetch_comments_with_replies(self):
        client = FakeClient()
        node = fetch_discussion_comments(client, "D_7")
        self.assertEqual(node["title"], "帖子")
        self.assertEqual(node["url"], "https://github.com/u/r/discussions/7")
        self.assertEqual(node["comment_total"], 2)
        self.assertTrue(node["is_answered"])
        self.assertEqual(len(node["comments"]), 2)
        top = node["comments"][0]
        self.assertEqual(top["author"], "访客")
        self.assertFalse(top["is_owner"])
        self.assertEqual(top["body"], "问题")
        self.assertEqual(top["created_at"], "2026-10-01T00:00:00Z")
        self.assertFalse(top["is_answer"])
        self.assertEqual(len(top["replies"]), 1)
        self.assertEqual(top["replies"][0]["author"], "作者")
        self.assertTrue(top["replies"][0]["is_owner"])
        self.assertEqual(top["replies"][0]["body"], "回复")
        self.assertEqual(top["replies"][0]["created_at"], "2026-10-01T01:00:00Z")
        self.assertTrue(top["replies"][0]["is_answer"])
        anon = node["comments"][1]
        self.assertEqual(anon["author"], "未知用户")
        self.assertEqual(anon["body"], "匿名")

    def test_fetch_missing_node_returns_none(self):
        class EmptyClient:
            def execute(self, query, variables=None):
                return {"node": None}
        self.assertIsNone(fetch_discussion_comments(EmptyClient(), "D_gone"))

    def test_non_discussion_node_returns_none(self):
        """内联片段未命中（id 指向 Issue 等）时必须按不存在处理。"""
        class IssueNode:
            def execute(self, query, variables=None):
                return {"node": {"title": "不是讨论"}}
        self.assertIsNone(fetch_discussion_comments(IssueNode(), "I_1"))

    def test_query_uses_node_field_not_top_level_discussion(self):
        """回归：顶层 Query 没有 discussion(id:)（线上 undefinedField）。"""
        from userscript_manager.discussions import DISCUSSION_NODE_QUERY
        self.assertIn("node(id: $id)", DISCUSSION_NODE_QUERY)
        self.assertIn("... on Discussion", DISCUSSION_NODE_QUERY)
        self.assertNotIn("discussion(id:", DISCUSSION_NODE_QUERY)


if __name__ == "__main__":
    unittest.main()
