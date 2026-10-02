import unittest
from datetime import datetime, timezone

from userscript_manager.issue_stats import (
    build_query, clip, fetch_stats, relative_time,
)


class FakeClient:
    """GraphQL 客户端测试替身：返回预置 data 或抛错。"""
    def __init__(self, data=None, error=None):
        self.data = data
        self.error = error
        self.calls = []

    def execute(self, query, variables=None):
        self.calls.append((query, variables))
        if self.error:
            raise self.error
        return self.data


def make_repo_data():
    return {
        "repository": {
            "d0": {
                "number": 2,
                "url": "https://github.com/t/r/issues/2",
                "state": "CLOSED",
                "comments": {
                    "totalCount": 8,
                    "nodes": [
                        {"author": {"login": "访客"}, "authorAssociation": "NONE",
                         "body": "百度首页右侧还有广告", "createdAt": "2026-09-29T10:00:00Z"},
                        {"author": {"login": "ACG-Q"}, "authorAssociation": "OWNER",
                         "body": "已修复，更新到 v1.0.1 即可。", "createdAt": "2026-10-01T06:00:00Z"},
                    ],
                },
            }
        }
    }


SCRIPTS = [
    {"id": "abc123", "issue": {"number": 2}},
    {"id": "no-issue"},
]


class TestFetchStats(unittest.TestCase):
    """fetch_stats：回复排序、别名批量查询、失败降级 None。"""
    def test_fetch_parses_replies_in_chronological_order(self):
        client = FakeClient(make_repo_data())
        out = fetch_stats(client, "t", "r", SCRIPTS)
        st = out["abc123"]
        self.assertEqual(st.reply_count, 8)
        self.assertTrue(st.is_closed)
        self.assertEqual(len(st.replies), 2)
        self.assertEqual(st.replies[-1].author, "ACG-Q")
        self.assertTrue(st.replies[-1].is_owner)
        self.assertIn("v1.0.1", st.replies[-1].body)
        self.assertFalse(st.replies[0].is_owner)

    def test_fetch_single_request_with_alias_and_skips_missing_nodes(self):
        client = FakeClient({"repository": {"d0": None}})
        out = fetch_stats(client, "t", "r", SCRIPTS)
        self.assertEqual(out, {})
        self.assertEqual(len(client.calls), 1)
        query, variables = client.calls[0]
        self.assertIn("d0: issue(number: $n0)", query)
        self.assertEqual(variables, {"owner": "t", "name": "r", "n0": 2})

    def test_fetch_returns_none_on_error(self):
        client = FakeClient(error=RuntimeError("boom"))
        self.assertIsNone(fetch_stats(client, "t", "r", SCRIPTS))

    def test_fetch_no_targets_makes_no_request(self):
        client = FakeClient()
        self.assertEqual(fetch_stats(client, "t", "r", [{"id": "x"}]), {})
        self.assertEqual(client.calls, [])

    def test_fetch_null_author_becomes_placeholder(self):
        data = make_repo_data()
        data["repository"]["d0"]["comments"]["nodes"][1]["author"] = None
        out = fetch_stats(FakeClient(data), "t", "r", SCRIPTS)
        self.assertEqual(out["abc123"].replies[-1].author, "未知用户")

    def test_open_state_maps_to_not_closed(self):
        data = make_repo_data()
        data["repository"]["d0"]["state"] = "OPEN"
        out = fetch_stats(FakeClient(data), "t", "r", SCRIPTS)
        self.assertFalse(out["abc123"].is_closed)


class TestHelpers(unittest.TestCase):
    """统计辅助函数：relative_time/clip/build_query。"""
    def test_relative_time_units(self):
        now = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(relative_time("2026-10-01T11:59:30Z", now), "刚刚")
        self.assertEqual(relative_time("2026-10-01T11:30:00Z", now), "30 分钟前")
        self.assertEqual(relative_time("2026-10-01T09:00:00Z", now), "3 小时前")
        self.assertEqual(relative_time("2026-09-29T12:00:00Z", now), "2 天前")
        self.assertEqual(relative_time("2026-07-15T12:00:00Z", now), "2026-07-15")

    def test_relative_time_empty_or_invalid_returns_placeholder(self):
        # createdAt 缺失时 issue_stats 会给 ""，不能让整站构建崩溃
        self.assertEqual(relative_time(""), "—")
        self.assertEqual(relative_time("not-a-date"), "—")

    def test_clip(self):
        self.assertEqual(clip("abcdef", 3), "abc…")
        self.assertEqual(clip("abc", 5), "abc")
        self.assertEqual(clip("a\nb  c", 10), "a b c")

    def test_build_query_aliases_scale(self):
        q = build_query(2)
        self.assertIn("$n0: Int!", q)
        self.assertIn("$n1: Int!", q)
        self.assertIn("d0: issue", q)
        self.assertIn("d1: issue", q)
        self.assertIn("comments(last: 2)", q)


if __name__ == "__main__":
    unittest.main(verbosity=2)
