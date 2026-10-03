"""行为基线（golden）：把幂等投影的逐字符契约钉死在 tests/golden/ 下。

投影器靠「Issue 标题/正文逐字符一致」决定是否更新（project_issues.py）——
模板一旦悄悄改动，线上会把所有 Issue 判为过期并触发全量重写。此前的 noop
用例（test_projector）两侧都调同一个 builder，属于**同源比较**，builder 变了
测试照样绿；本模块用提交进仓库的基线文件提供独立锚点。

改模板前请显式更新基线，diff 会出现在 code review 里：

    UPDATE_GOLDEN=1 python -m pytest tests/test_golden.py
"""

import os
import unittest
from pathlib import Path

from tests._helpers import FRESH_REGISTRY, ConfigIsolation
from userscript_manager.config import CONFIG
from userscript_manager.issue_page import (
    build_discussion_body,
    build_issue_body,
    build_title,
    script_id_from_body,
)
from userscript_manager.registry import save_registry

GOLDEN_DIR = Path(__file__).parent / "golden"

# 确定性样本：时间戳/版本号写死，名称带竖线以锁定 escape_md_cell 行为
CANONICAL = {
    "id": "golden01",
    "type": "self",
    "name": "基线脚本 | 演示",
    "version": "1.2.3",
    "description": "用于锁定输出基线的脚本",
    "author": "基线作者",
    "namespace": "https://example.com",
    "match": ["*://a/*", "*://b/*"],
    "grant": ["none"],
    "enabled": True,
    "source_url": None,
    "source_type": None,
    "created_at": "2026-01-02T03:04:05Z",
    "updated_at": "2026-01-03T04:05:06Z",
    "last_synced_at": None,
    "sync_enabled": False,
    "deleted": False,
    "documentation": "# 文档\n\n含 **Markdown** 的文档。",
    "changelog": [
        {"version": "1.2.3", "date": "2026-01-03", "note": "修复"},
        {"version": "1.2.0", "date": "2026-01-01", "note": "初始版本"},
    ],
    "discussions": [
        {"version": "1.2.3", "number": 9, "node_id": "D_9",
         "url": "https://github.com/o/r/discussions/9", "created_at": "2026-01-03"},
        {"version": "1.2.0", "number": 7, "node_id": "D_7",
         "url": "https://github.com/o/r/discussions/7", "created_at": "2026-01-01"},
    ],
    "issue": {"number": 4, "node_id": "I_4",
              "url": "https://github.com/o/r/issues/4"},
}


class TestGoldenProjection(ConfigIsolation):
    """模板输出与仓库内基线逐字符对拍。"""

    TMP_PREFIX = "usm_golden_"

    def _config_setup(self):
        CONFIG["registry_file"].write_text(FRESH_REGISTRY, encoding="utf-8")

    @staticmethod
    def _registry_json() -> str:
        """走真实的 save_registry 落盘，锁定 JSON 序列化格式（键序/缩进/转义）。"""
        save_registry({"schema": 1, "scripts": [dict(CANONICAL)]})
        return Path(CONFIG["registry_file"]).read_text(encoding="utf-8")

    def _actual(self) -> dict:
        return {
            "issue_title.txt": build_title(CANONICAL),
            "issue_body.md": build_issue_body(CANONICAL),
            "discussion_body.md": build_discussion_body(
                CANONICAL, prev_version="1.2.0"),
            "registry_format.json": self._registry_json(),
        }

    def test_outputs_match_golden_files(self):
        actual = self._actual()
        if os.environ.get("UPDATE_GOLDEN"):
            GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            for name, content in actual.items():
                (GOLDEN_DIR / name).write_text(content, encoding="utf-8")
            self.skipTest(f"已更新 {len(actual)} 个基线文件，请用 git diff 复核")

        for name, content in actual.items():
            path = GOLDEN_DIR / name
            self.assertTrue(
                path.exists(),
                f"缺少基线 tests/golden/{name}，"
                "运行 UPDATE_GOLDEN=1 python -m pytest tests/test_golden.py 生成",
            )
            self.assertEqual(
                content, path.read_text(encoding="utf-8"),
                f"{name} 与基线不一致：投影模板的改动必须显式更新 "
                f"tests/golden/{name}（UPDATE_GOLDEN=1），否则线上会把全部 "
                "Issue 判为过期并触发全量重写",
            )

    def test_marker_roundtrip(self):
        """对账标记必须能从生成的正文里原样取回（孤儿判定的依据）。"""
        self.assertEqual(script_id_from_body(build_issue_body(CANONICAL)),
                         CANONICAL["id"])
        self.assertIsNone(script_id_from_body("没有标记的正文"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
