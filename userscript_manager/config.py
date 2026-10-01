import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

CONFIG = {
    "author": {
        "name": os.getenv("AUTHOR_NAME", "Your Name"),
        "namespace": os.getenv("AUTHOR_NAMESPACE", "https://your-namespace.com"),
    },
    "registry_file": PROJECT_ROOT / "registry.json",
    "self_scripts_dir": PROJECT_ROOT / "scripts" / "self",
    "synced_scripts_dir": PROJECT_ROOT / "scripts" / "synced",
    "dist_dir": PROJECT_ROOT / "dist",
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
        return CONFIG["github_pages"]["base_url"].rstrip("/")
    repo = CONFIG["github_repo"]
    owner, name = repo.split("/") if "/" in repo else (repo, "")
    return f"https://{owner}.github.io/{name}"

def get_install_url(script_id: str) -> str:
    """Generate install/update URL for a script via GitHub Pages."""
    base = get_pages_base_url()
    return f"{base}/dist/{script_id}.user.js"