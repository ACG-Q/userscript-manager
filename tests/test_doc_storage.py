import io
import sys
import tempfile
import unittest
from pathlib import Path

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from userscript_manager.config import CONFIG
from userscript_manager.registry import load_registry
from userscript_manager.utils import ensure_dirs

from userscript_manager.commands import get_command
import userscript_manager.commands.add
import userscript_manager.commands.update

CODE = (
    "// ==UserScript==\n"
    "// @name Doc Demo\n"
    "// @version 1.0.0\n"
    "// @match *://*/*\n"
    "// @grant none\n"
    "// ==/UserScript==\n"
    "console.log(1);\n"
)
FENCED = "```javascript\n" + CODE + "```"

_SAVED_KEYS = (
    "registry_file",
    "self_scripts_dir",
    "synced_scripts_dir",
    "dist_dir",
    "github_repo",
)


class TestDocumentationStorage(unittest.TestCase):
    """Regression tests: code-only comments must not overwrite documentation (C1).

    Config is redirected per-test and restored in tearDown so that modules
    relying on module-level CONFIG isolation (test_sync, test_regression)
    keep seeing their own state.
    """

    def setUp(self):
        self._saved = {key: CONFIG[key] for key in _SAVED_KEYS}
        self._saved_base_url = CONFIG["github_pages"]["base_url"]
        tmp = Path(tempfile.mkdtemp(prefix="usm_docstorage_"))
        CONFIG["registry_file"] = tmp / "registry.json"
        CONFIG["self_scripts_dir"] = tmp / "scripts" / "self"
        CONFIG["synced_scripts_dir"] = tmp / "scripts" / "synced"
        CONFIG["dist_dir"] = tmp / "dist"
        CONFIG["github_repo"] = "testuser/testrepo"
        CONFIG["github_pages"]["base_url"] = ""
        ensure_dirs()
        CONFIG["registry_file"].write_text(
            '{"schema": 1, "scripts": []}', encoding="utf-8"
        )
        self.registry = load_registry()

    def tearDown(self):
        for key, value in self._saved.items():
            CONFIG[key] = value
        CONFIG["github_pages"]["base_url"] = self._saved_base_url

    def _readme(self, script_id: str):
        path = CONFIG["self_scripts_dir"] / script_id / "README.md"
        return path.read_text(encoding="utf-8") if path.exists() else None

    def test_add_only_code_block_leaves_documentation_empty(self):
        cmd = get_command("add")
        cmd(self.registry, "", CODE, FENCED, True)
        script = self.registry["scripts"][0]
        self.assertEqual(script["documentation"], "")
        self.assertIsNone(self._readme(script["id"]))

    def test_add_prose_with_code_keeps_full_markdown(self):
        md = "## 用法\n\n保留这个说明。\n\n" + FENCED
        cmd = get_command("add")
        cmd(self.registry, "", CODE, md, True)
        script = self.registry["scripts"][0]
        self.assertEqual(script["documentation"], md)
        self.assertEqual(self._readme(script["id"]), md)

    def test_up_only_code_keeps_existing_documentation(self):
        md = "## 原有文档\n\n不能被覆盖。"
        add = get_command("add")
        add(self.registry, "", CODE, md, True)
        script = self.registry["scripts"][0]
        readme_before = self._readme(script["id"])

        up = get_command("up")
        up(self.registry, script["id"], CODE, FENCED, True)

        reloaded = load_registry()["scripts"][0]
        self.assertEqual(reloaded["documentation"], md)
        self.assertEqual(self._readme(script["id"]), readme_before)

    def test_up_prose_replaces_documentation(self):
        md_old = "旧文档"
        add = get_command("add")
        add(self.registry, "", CODE, md_old, True)
        script = self.registry["scripts"][0]

        md_new = "## 新文档\n\n" + FENCED
        up = get_command("up")
        up(self.registry, script["id"], CODE, md_new, True)

        reloaded = load_registry()["scripts"][0]
        self.assertEqual(reloaded["documentation"], md_new)
        self.assertEqual(self._readme(script["id"]), md_new)

    def test_add_sync_rejects_non_userscript_content(self):
        import userscript_manager.commands.add as add_mod
        from userscript_manager.sources.base import ScriptSource

        class FakeAdapter:
            name = "Fake"

            def fetch(self, url):
                return ScriptSource(
                    code="<html>not a script</html>",
                    meta={},
                    source_url=url,
                    source_type="direct",
                )

        original = add_mod.get_adapter
        add_mod.get_adapter = lambda url: FakeAdapter()
        try:
            result = get_command("add")(
                self.registry, "https://example.com/x.js", "", "", False
            )
        finally:
            add_mod.get_adapter = original

        self.assertIn("不是有效的油猴脚本", result)
        self.assertEqual(self.registry["scripts"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
