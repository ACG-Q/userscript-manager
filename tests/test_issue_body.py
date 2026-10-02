import io
import os
import sys
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from tests._helpers import ConfigIsolation
from userscript_manager.issue_page import (
    build_issue_body, build_marker, build_title,
    script_id_from_body, tombstone_body, tombstone_title,
)


def make_script(**overrides):
    script = {
        "id": "abc123", "type": "self", "name": "甲", "version": "1.0.1",
        "author": "作者", "match": ["*://a/*"], "documentation": "# 文档正文",
        "changelog": [{"version": "1.0.1", "date": "2026-10-01", "note": "手动更新"}],
    }
    script.update(overrides)
    return script


class TestIssueBody(ConfigIsolation):
    """Issue 正文生成：标记往返、转义、文档与 changelog 渲染。"""
    REDIRECT_PATHS = False

    def test_marker_is_first_line_and_roundtrips(self):
        body = build_issue_body(make_script())
        first = body.splitlines()[0]
        self.assertEqual(first, build_marker("abc123"))
        self.assertEqual(script_id_from_body(body), "abc123")

    def test_script_id_from_body_returns_none_without_marker(self):
        self.assertIsNone(script_id_from_body("# 普通正文"))
        self.assertIsNone(script_id_from_body(""))

    def test_metadata_table_contains_escaped_fields(self):
        script = make_script(name="甲|乙", version="1.0.1")
        body = build_issue_body(script)
        self.assertIn("甲\\|乙", body)
        self.assertIn("| 版本 | 1.0.1 |", body)
        self.assertIn("[安装脚本](https://testuser.github.io/testrepo/dist/abc123.user.js)", body)

    def test_documentation_rendered_verbatim(self):
        body = build_issue_body(make_script(documentation="## 用法\n\n- 点击"))
        self.assertIn("## 用法", body)

    def test_changelog_rows_rendered_newest_first(self):
        script = make_script(changelog=[
            {"version": "1.0.1", "date": "2026-10-01", "note": "手动更新"},
            {"version": "1.0.0", "date": "2026-09-30", "note": "初始版本"},
        ])
        body = build_issue_body(script)
        self.assertLess(body.index("1.0.1"), body.index("1.0.0"))

    def test_empty_changelog_placeholder(self):
        body = build_issue_body(make_script(changelog=[]))
        self.assertIn("暂无更新记录", body)

    def test_build_is_deterministic(self):
        script = make_script()
        self.assertEqual(build_issue_body(script), build_issue_body(script))

    def test_title_escapes(self):
        self.assertEqual(build_title(make_script(name="A|B")), "📝 A\\|B")

    def test_tombstone_has_no_marker_and_prefixes_title(self):
        self.assertNotIn("script-id", tombstone_body("甲"))
        self.assertTrue(tombstone_title("📝 甲").startswith("[已删除]"))
        self.assertEqual(tombstone_title("[已删除] 📝 甲"), "[已删除] 📝 甲")


if __name__ == "__main__":
    unittest.main(verbosity=2)
