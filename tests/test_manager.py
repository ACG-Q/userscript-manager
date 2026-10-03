import io
import os
import sys
import unittest

if (sys.stdout.encoding or "").lower().replace("-", "") != "utf8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import manager
from tests._helpers import FRESH_REGISTRY, ConfigIsolation
from userscript_manager.commands import _commands
from userscript_manager.config import CONFIG

_ENV_KEYS = ("COMMENT_BODY", "COMMENT_USER", "REPO_OWNER", "ISSUE_NUMBER")


class TestManagerFlow(ConfigIsolation):
    """manager.main 的每条早退路径都必须落结果文件，否则 Actions 会误报「操作完成」。"""

    TMP_PREFIX = "usm_mgr_"

    def _config_setup(self):
        CONFIG["registry_file"].write_text(FRESH_REGISTRY, encoding="utf-8")

    def setUp(self):
        super().setUp()
        self._saved_env = {k: os.environ.get(k) for k in _ENV_KEYS}
        self._saved_cwd = os.getcwd()
        os.chdir(self._tmp)
        self._result_file = self._tmp / "command_result.txt"
        if self._result_file.exists():
            self._result_file.unlink()

    def tearDown(self):
        try:
            for key, value in self._saved_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            os.chdir(self._saved_cwd)
            _commands.pop("boom", None)
        finally:
            super().tearDown()

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

    def test_non_panel_issue_is_ignored(self):
        result = self._run("/list", issue="2")
        self.assertIsNotNone(result)
        self.assertIn("非命令面板", result)

    def test_invalid_issue_number_is_reported(self):
        result = self._run("/list", issue="abc")
        self.assertIsNotNone(result)
        self.assertIn("无效的 ISSUE_NUMBER", result)

    def test_all_expected_commands_registered(self):
        from userscript_manager.commands import get_all_commands

        expected = {
            "list", "add", "up", "sync", "sync-all", "rm",
            "info", "enable", "disable", "export",
        }
        self.assertEqual(expected, set(get_all_commands()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
