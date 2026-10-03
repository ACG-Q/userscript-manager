"""测试共用隔离设施：按测试重定向全局 CONFIG，tearDown 原样还原。

历史上多个测试文件在模块加载时无条件改写 CONFIG（路径/仓库键），
导致执行顺序影响结果——单跑通过、全量失败（或反之）。所有涉及
CONFIG 的测试类改继承 ConfigIsolation，消除顺序耦合。
"""
import tempfile
import unittest
from pathlib import Path

from userscript_manager.config import CONFIG
from userscript_manager.utils import ensure_dirs

_PATH_KEYS = (
    "registry_file",
    "self_scripts_dir",
    "synced_scripts_dir",
    "dist_dir",
    "archive_file",
)

FRESH_REGISTRY = '{"schema": 1, "scripts": []}'


class ConfigIsolation(unittest.TestCase):
    """把 CONFIG 的路径键与 repo/base_url 重定向到确定值的测试基类。

    - ``REDIRECT_PATHS = True``（默认）：四个路径键指向每测试独立的临时目录；
      设为 False 则只固定 ``github_repo`` / ``base_url``，不动文件系统。
    - 子类覆写 ``_config_setup`` 做附加准备（如写入空注册表并 ``load_registry``），
      覆写 ``_config_teardown`` 做清理（如 ``os.chdir`` 还原由子类 tearDown 负责）。
    """

    TMP_PREFIX = "usm_t_"
    REDIRECT_PATHS = True

    def setUp(self):
        super().setUp()
        self._saved = {key: CONFIG[key] for key in _PATH_KEYS}
        self._saved_repo = CONFIG["github_repo"]
        self._saved_base = CONFIG["github_pages"]["base_url"]
        self._tmp = Path(tempfile.mkdtemp(prefix=self.TMP_PREFIX))
        if self.REDIRECT_PATHS:
            CONFIG["registry_file"] = self._tmp / "registry.json"
            CONFIG["self_scripts_dir"] = self._tmp / "scripts" / "self"
            CONFIG["synced_scripts_dir"] = self._tmp / "scripts" / "synced"
            CONFIG["dist_dir"] = self._tmp / "dist"
            CONFIG["archive_file"] = self._tmp / "archive" / "commands.json"
            ensure_dirs()
        CONFIG["github_repo"] = "testuser/testrepo"
        CONFIG["github_pages"]["base_url"] = ""
        self._config_setup()

    def tearDown(self):
        try:
            self._config_teardown()
        finally:
            for key, value in self._saved.items():
                CONFIG[key] = value
            CONFIG["github_repo"] = self._saved_repo
            CONFIG["github_pages"]["base_url"] = self._saved_base
            super().tearDown()

    def _config_setup(self):
        """子类钩子：写空注册表、load_registry 等额外准备。"""

    def _config_teardown(self):
        """子类钩子：测试专属清理（还原 cwd 等）。"""
