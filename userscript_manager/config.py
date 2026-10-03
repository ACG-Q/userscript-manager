import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).parent.parent

# 异构配置表（路径 / 字符串 / 嵌套字典）：显式标注为 dict[str, Any]，
# 否则 mypy 会把它推断成 dict[str, object] 并在所有下标处报错。
CONFIG: dict[str, Any] = {
    "author": {
        # 用 `or` 而非 getenv 默认值：workflow 透传的 vars 未配置时是空串而非未设置
        "name": os.getenv("AUTHOR_NAME") or "Your Name",
        "namespace": os.getenv("AUTHOR_NAMESPACE") or "https://your-namespace.com",
    },
    "registry_file": PROJECT_ROOT / "registry.json",
    "self_scripts_dir": PROJECT_ROOT / "scripts" / "self",
    "synced_scripts_dir": PROJECT_ROOT / "scripts" / "synced",
    "dist_dir": PROJECT_ROOT / "dist",
    # 命令面板历史评论归档账本：panel_cleanup.py 写入，站点生成器读取
    "archive_file": PROJECT_ROOT / "archive" / "commands.json",
    "github_repo": os.getenv("GITHUB_REPOSITORY", "owner/repo"),
    "branch": os.getenv("GITHUB_REF_NAME", "main"),
    "github_pages": {
        "enabled": True,
        "base_url": os.getenv("GITHUB_PAGES_URL", ""),  # e.g. https://user.github.io/repo
    },
    "control_issue_number": 1,  # 硬编码：Issue #1 为命令面板
}

def get_pages_base_url() -> str:
    """Get GitHub Pages base URL for dist files."""
    if CONFIG["github_pages"]["base_url"]:
        return str(CONFIG["github_pages"]["base_url"]).rstrip("/")
    repo = CONFIG["github_repo"]
    owner, name = repo.split("/") if "/" in repo else (repo, "")
    return f"https://{owner}.github.io/{name}"

def get_install_url(script_id: str) -> str:
    """Generate install/update URL for a script via GitHub Pages."""
    base = get_pages_base_url()
    return f"{base}/dist/{script_id}.user.js"