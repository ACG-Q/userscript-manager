import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from userscript_manager.config import CONFIG
from userscript_manager.commands import _commands

import manager

_ENV_KEYS = ("COMMENT_BODY", "COMMENT_USER", "REPO_OWNER", "ISSUE_NUMBER")
_CFG_KEYS = (
    "registry_file",
    "self_scripts_dir",
    "synced_scripts_dir",
    "dist_dir",
    "github_repo",
)


class TestManagerFlow(unittest.TestCase):
    """manager.main 的每条早退路径都必须落结果文件，否则 Actions 会误报「操作完成」。"""

    def setUp(self):
        self._saved_env = {k: os.environ.get(k) for k in _ENV_KEYS}
        self._saved_cwd = os.getcwd()
        self._saved_cfg = {k: CONFIG[k] for k in _CFG_KEYS}
        self._saved_base_url = CONFIG["github_pages"]["base_url"]
        self._tmp = Path(tempfile.mkdtemp(prefix="usm_mgr_"))
        os.chdir(self._tmp)
        CONFIG["registry_file"] = self._tmp / "registry.json"
        CONFIG["self_scripts_dir"] = self._tmp / "scripts" / "self"
        CONFIG["synced_scripts_dir"] = self._tmp / "scripts" / "synced"
        CONFIG["dist_dir"] = self._tmp / "dist"
        CONFIG["github_repo"] = "testuser/testrepo"
        CONFIG["github_pages"]["base_url"] = ""
        CONFIG["registry_file"].write_text(
            '{"schema": 1, "scripts": []}', encoding="utf-8"
        )
        self._result_file = self._tmp / "command_result.txt"
        if self._result_file.exists():
            self._result_file.unlink()

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        os.chdir(self._saved_cwd)
        for key, value in self._saved_cfg.items():
            CONFIG[key] = value
        CONFIG["github_pages"]["base_url"] = self._saved_base_url
        _commands.pop("boom", None)

    def _run(self, body, user="owner", owner="owner", issue=""):
        os.environ["COMMENT_BODY"] = body
        os.environ["COMMENT_USER"] = user
        os.environ["REPO_OWNER"] = owner
        os.environ["ISSUE_NUMBER"] = issue
        manager.main()
        if self._result_file.exists():
            return self._result_file.read_text(encoding="utf-8")
        return None

    def test_success_writes_result_file(self):
        result = self._run("/list")
        self.assertIsNotNone(result)
        self.assertIn("没有脚本", result)

    def test_unknown_command_writes_result_file(self):
        result = self._run("/definitely-not-a-command")
        self.assertIsNotNone(result)
        self.assertIn("未知命令", result)

    def test_unrecognized_comment_writes_result_file(self):
        result = self._run("这只是一句普通评论")
        self.assertIsNotNone(result)
        self.assertIn("未识别命令", result)

    def test_permission_denied_writes_result_file(self):
        result = self._run("/list", user="mallory", owner="owner")
        self.assertIsNotNone(result)
        self.assertIn("权限不足", result)

    def test_command_exception_is_caught_and_reported(self):
        from userscript_manager.commands import register

        @register("boom")
        def boom(*_args):
            raise RuntimeError("炸了")

        result = self._run("/boom")
        self.assertIsNotNone(result)
        self.assertIn("内部错误", result)
        self.assertIn("boom", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
