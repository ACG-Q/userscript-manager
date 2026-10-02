import io
import os
import sys
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from tests._helpers import ConfigIsolation
from userscript_manager.issue_page import (
    build_discussion_body, build_discussion_title, build_issue_body,
    build_issue_index, build_marker, build_title, script_id_from_body,
    tombstone_body, tombstone_title,
)


def make_script(**overrides):
    script = {
        "id": "abc123", "type": "self", "name": "甲", "version": "1.0.1",
        "author": "作者", "match": ["*://a/*"], "documentation": "# 文档正文",
        "description": "演示描述",
        "changelog": [{"version": "1.0.1", "date": "2026-10-01", "note": "手动更新"}],
        "discussions": [], "deleted": False, "enabled": True,
        "source_url": None, "source_type": None,
        "issue": {"number": 5, "node_id": "I_5",
                  "url": "https://github.com/testuser/testrepo/issues/5"},
    }
    script.update(overrides)
    return script


class TestIssueBody(ConfigIsolation):
    """活字段正文：状态/索引/来源，文档与更新历史移出（D5）。"""
    REDIRECT_PATHS = False

    def test_marker_is_first_line_and_roundtrips(self):
        body = build_issue_body(make_script())
        first = body.splitlines()[0]
        self.assertEqual(first, build_marker("abc123"))
        self.assertEqual(script_id_from_body(body), "abc123")

    def test_script_id_from_body_returns_none_without_marker(self):
        self.assertIsNone(script_id_from_body("# 普通正文"))
        self.assertIsNone(script_id_from_body(""))

    def test_active_table_contains_escaped_name_and_install(self):
        body = build_issue_body(make_script(name="甲|乙"))
        self.assertIn("| 状态 | ✅ 已启用 |", body)
        self.assertIn("| 最新版本 | 1.0.1 |", body)
        self.assertIn("| 名称 | 甲\\|乙 |", body)
        self.assertIn("[安装脚本](https://testuser.github.io/testrepo/dist/abc123.user.js)", body)

    def test_status_disabled_when_enabled_false(self):
        body = build_issue_body(make_script(enabled=False))
        self.assertIn("| 状态 | ⏸️ 已停用 |", body)

    def test_status_deleted_when_flagged(self):
        body = build_issue_body(make_script(deleted=True))
        self.assertIn("| 状态 | 🗑️ 已删除 |", body)

    def test_missing_version_renders_dash(self):
        body = build_issue_body(make_script(version=None))
        self.assertIn("| 最新版本 | - |", body)

    def test_source_row_self_written_and_external(self):
        self.assertIn("| 来源 | 自写（本仓库） |", build_issue_body(make_script()))
        body = build_issue_body(make_script(
            source_url="https://greasyfork.org/zh-CN/scripts/1234",
            source_type="greasyfork"))
        self.assertIn(
            "| 来源 | greasyfork · [来源页](https://greasyfork.org/zh-CN/scripts/1234) |",
            body)

    def test_empty_index_placeholder(self):
        body = build_issue_body(make_script())
        self.assertIn("## 版本讨论帖", body)
        self.assertIn("| - | - | 暂无版本帖 |", body)

    def test_index_reversed_with_v_prefix_and_link(self):
        script = make_script(discussions=[
            {"version": "1.0.0", "number": 7, "node_id": "D_7",
             "url": "https://github.com/u/r/discussions/7", "created_at": "2026-08-20"},
            {"version": "1.0.1", "number": 9, "node_id": "D_9",
             "url": "https://github.com/u/r/discussions/9", "created_at": "2026-10-01"},
        ])
        seg = build_issue_body(script).split("## 版本讨论帖", 1)[1]
        self.assertIn(
            "| v1.0.1 | 2026-10-01 | [讨论 #9 →](https://github.com/u/r/discussions/9) |",
            seg)
        self.assertLess(seg.index("v1.0.1"), seg.index("v1.0.0"))

    def test_docs_and_changelog_moved_out_of_issue(self):
        body = build_issue_body(make_script())
        self.assertNotIn("## 文档", body)
        self.assertNotIn("## 更新历史", body)
        self.assertNotIn("手动更新", body)

    def test_build_is_deterministic(self):
        script = make_script()
        self.assertEqual(build_issue_body(script), build_issue_body(script))

    def test_title_escapes(self):
        self.assertEqual(build_title(make_script(name="A|B")), "📝 A\\|B")

    def test_tombstone_has_no_marker_and_prefixes_title(self):
        self.assertNotIn("script-id", tombstone_body("甲"))
        self.assertTrue(tombstone_title("📝 甲").startswith("[已删除]"))
        self.assertEqual(tombstone_title("[已删除] 📝 甲"), "[已删除] 📝 甲")

    def test_tombstone_appends_discussion_backlinks(self):
        discussions = [
            {"version": "1.0.1", "number": 9, "node_id": "D_9",
             "url": "https://github.com/u/r/discussions/9", "created_at": "2026-10-01"},
        ]
        body = tombstone_body("甲", discussions)
        self.assertIn("历史版本帖", body)
        self.assertIn("[v1.0.1 · #9](https://github.com/u/r/discussions/9)", body)
        self.assertNotIn("script-id", body)

    def test_tombstone_without_discussions_omits_section(self):
        body = tombstone_body("甲")
        self.assertNotIn("历史版本帖", body)

    def test_build_issue_index_empty_states(self):
        self.assertEqual(build_issue_index([]), "| - | - | 暂无版本帖 |")


class TestDiscussionPost(ConfigIsolation):
    """版本帖标题与正文快照（D1/D2/D6）。"""
    REDIRECT_PATHS = False

    def test_title_with_version(self):
        title = build_discussion_title(make_script(), today="2026-10-02")
        self.assertEqual(title, "[v1.0.1] 甲 2026-10-02")

    def test_title_missing_version_uses_initial(self):
        title = build_discussion_title(make_script(version=None), today="2026-10-02")
        self.assertEqual(title, "[初始版本] 甲 2026-10-02")

    def test_body_first_release(self):
        body = build_discussion_body(make_script(), prev_version=None)
        self.assertIn("首次发布 **v1.0.1**：手动更新", body)
        self.assertNotIn("更新至", body)

    def test_body_upgrade_transition(self):
        body = build_discussion_body(make_script(), prev_version="1.0.0")
        self.assertIn("自 v1.0.0 更新至 **v1.0.1**：手动更新", body)
        self.assertNotIn("首次发布", body)

    def test_body_snapshot_docs_changelog_and_backlinks(self):
        body = build_discussion_body(make_script(), prev_version=None)
        self.assertNotIn("script-id", body)
        self.assertIn("| 作者 | 作者 |", body)
        self.assertIn("| 匹配规则 | `*://a/*` |", body)
        self.assertIn("## 描述", body)
        self.assertIn("演示描述", body)
        self.assertIn("## 文档", body)
        self.assertIn("# 文档正文", body)
        self.assertIn("## 更新历史", body)
        self.assertIn("| 1.0.1 | 2026-10-01 | 手动更新 |", body)
        self.assertIn(
            "[Issue #5（状态与索引）](https://github.com/testuser/testrepo/issues/5)",
            body)
        self.assertIn(
            "[脚本详情页](https://testuser.github.io/testrepo/scripts/abc123.html)",
            body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
