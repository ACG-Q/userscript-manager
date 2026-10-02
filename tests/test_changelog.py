import io
import os
import sys
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
os.environ["GITHUB_REPOSITORY"] = "testuser/testrepo"

from tests._helpers import ConfigIsolation
from userscript_manager.registry import load_registry, save_registry
from userscript_manager.utils import add_changelog
from userscript_manager.issue_parser import parse_comment
from userscript_manager.commands import get_command
import userscript_manager.commands.add
import userscript_manager.commands.update
import userscript_manager.commands.sync

SCRIPT = """// ==UserScript==
// @name 脚本甲
// @version 1.0.0
// @match *://*/*
// @grant none
// ==/UserScript==
body();
"""


class TestChangelog(ConfigIsolation):
    TMP_PREFIX = "usm_cl_"

    def _config_setup(self):
        self.registry = load_registry()

    def _run(self, body):
        p = parse_comment(body)
        result = get_command(p.command)(self.registry, p.args, p.code, p.markdown, p.has_code_block)
        save_registry(self.registry)
        return result

    def test_helper_prepends_row_with_iso_date(self):
        script = {"version": "2.0.0"}
        add_changelog(script, "备注")
        self.assertEqual(script["changelog"][0]["version"], "2.0.0")
        self.assertEqual(script["changelog"][0]["note"], "备注")
        self.assertRegex(script["changelog"][0]["date"], r"^\d{4}-\d{2}-\d{2}$")

    def test_add_writes_initial_row(self):
        self._run("/add\n```javascript\n" + SCRIPT + "\n```")
        rows = self.registry["scripts"][0]["changelog"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["version"], "1.0.0")
        self.assertEqual(rows[0]["note"], "初始版本")

    def test_up_prepends_new_row(self):
        self._run("/add\n```javascript\n" + SCRIPT + "\n```")
        sid = self.registry["scripts"][0]["id"]
        self._run(f"/up {sid}\n```javascript\n" + SCRIPT + "\n```")
        rows = self.registry["scripts"][0]["changelog"]
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0]["version"], rows[0]["note"]), ("1.0.1", "手动更新"))
        self.assertEqual((rows[1]["version"], rows[1]["note"]), ("1.0.0", "初始版本"))

    def test_sync_version_change_prepends_row(self):
        script = {
            "id": "sync_cl", "type": "synced", "name": "S", "version": "1.0.0",
            "description": "", "author": "", "namespace": "", "match": ["*://*/*"],
            "grant": ["none"], "enabled": True,
            "source_url": "https://raw.githubusercontent.com/user/repo/main/s.js",
            "source_type": "direct",
            "sync_enabled": True, "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z", "last_synced_at": "2026-01-01T00:00:00Z",
            "custom_match": None, "documentation": "",
        }
        self.registry["scripts"].append(script)
        save_registry(self.registry)

        new_code = SCRIPT.replace("1.0.0", "1.1.0")
        import requests

        class FakeResp:
            def raise_for_status(self):
                pass

            @property
            def text(self):
                return new_code

        original_get = requests.get
        requests.get = lambda url, timeout=None: FakeResp()
        try:
            self._run("/sync sync_cl")
        finally:
            requests.get = original_get

        rows = self.registry["scripts"][0]["changelog"]
        self.assertEqual(len(rows), 1)
        self.assertEqual((rows[0]["version"], rows[0]["note"]), ("1.1.0", "上游同步"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
