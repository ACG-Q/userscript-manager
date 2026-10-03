"""软删除命令：条目保留（deleted: true）、文件清理，可由 /add 同源复活。"""
from typing import Any

from ..commands import register
from ..registry import find_script, find_script_by_source_url, save_registry
from ..utils import remove_dist_file, remove_source_dir


@register("rm")
def execute(registry: dict[str, Any], args: str, code: str,
            markdown: str, has_code_block: bool) -> str:
    """/rm <id|url>：软删除脚本——条目保留可复活，Issue 将转为墓碑。"""
    if not args:
        return "❌ 请提供要删除的 URL 或 ID，例如 /rm <url> 或 /rm <script_id>"

    if args.startswith("http://") or args.startswith("https://"):
        return remove_by_url(registry, args)
    return remove_by_id(registry, args)


def remove_by_url(registry: dict[str, Any], url: str) -> str:
    """按来源 URL 软删除同步脚本（未命中返回提示文本）。"""
    script = find_script_by_source_url(registry, url)
    if not script:
        return f"❌ 未找到来源为 {url} 的脚本。"
    if script.get("deleted"):
        return f"ℹ️ 脚本 {script['id']} 已处于删除状态。"
    _soft_delete(registry, script)
    return (
        f"🗑️ 已删除同步脚本 {script['id']}（来源 {url}；"
        "软删除，可重发 /add 复活）"
    )


def remove_by_id(registry: dict[str, Any], script_id: str) -> str:
    """按 ID 软删除：标 deleted、清源码与 dist，条目保留供复活。"""
    script = find_script(registry, script_id)
    if not script:
        return f"❌ 未找到 ID 为 {script_id} 的脚本。"
    if script.get("deleted"):
        return f"ℹ️ 脚本 {script_id} 已处于删除状态。"
    _soft_delete(registry, script)
    return f"🗑️ 已删除脚本 {script_id}（软删除：条目保留可复活，Issue 将转为墓碑）"


def _soft_delete(registry: dict[str, Any], script: dict[str, Any]) -> None:
    """标记软删并清理文件，随后落盘（软删除的唯一写入口）。"""
    script["deleted"] = True
    remove_source_dir(script)
    remove_dist_file(script["id"])
    save_registry(registry)
