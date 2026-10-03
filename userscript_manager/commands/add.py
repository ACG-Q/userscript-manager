from typing import Any

from ..commands import register
from ..config import CONFIG, get_install_url
from ..issue_parser import remove_code_blocks
from ..registry import add_script, find_script_by_source_url, save_registry
from ..sources import get_adapter
from ..utils import (
    add_changelog,
    build_dist_for_synced,
    build_userscript_header,
    ensure_dirs,
    extract_meta_from_code,
    format_js_code,
    generate_self_script_id,
    generate_synced_script_id,
    now_iso,
    save_documentation,
    write_dist_file,
    write_source_file,
)


@register("add")
def execute(registry: dict[str, Any], args: str, code: str,
            markdown: str, has_code_block: bool) -> str:
    """/add [url]：带 URL 走同步添加，否则按代码块自写添加。"""
    ensure_dirs()
    if args:
        return add_sync(registry, args)
    else:
        return add_self(registry, code, markdown, has_code_block)

def add_self(registry: dict[str, Any], code: str, markdown: str,
             has_code_block: bool) -> str:
    """把代码块解析为元数据后入库：格式化、写源码/dist/文档、记 changelog。"""
    if not has_code_block or not code.strip():
        return (
            "❌ 未提供脚本代码。请在 Markdown 代码块中提供脚本代码。\n"
            "示例：\n```javascript\n// ==UserScript==\n// @name 我的脚本\n"
            "// @version 1.0.0\n// ==/UserScript==\n(function() { ... })();\n```"
        )
    
    script_id = generate_self_script_id()
    # 自写脚本入库前统一格式化（同步脚本保持上游原文，见 design.md 6.3）
    code = format_js_code(code)
    meta = extract_meta_from_code(code)
    name = meta.get("name", f"Script-{script_id[:8]}")
    
    # A comment containing only a code block is not documentation; storing it
    # would overwrite real docs with the script source (C1).
    doc = markdown if remove_code_blocks(markdown).strip() else ""

    script_meta = {
        "id": script_id,
        "type": "self",
        "name": name,
        "version": meta.get("version", "1.0.0"),
        "description": meta.get("description", ""),
        "author": meta.get("author", CONFIG["author"]["name"]),
        "namespace": meta.get("namespace", CONFIG["author"]["namespace"]),
        "match": meta.get("match", ["*://*/*"]),
        "grant": meta.get("grant", ["none"]),
        "enabled": True,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "source_url": None,
        "source_type": None,
        "last_synced_at": None,
        "sync_enabled": False,
        "documentation": doc,
    }
    
    # Write source file (only the code, not markdown)
    write_source_file(script_meta, code)
    
    # Build and write dist file
    full_code = build_userscript_header(script_meta, code)
    write_dist_file(script_id, full_code)
    
    # Persist prose docs to the per-script README (content itself lives
    # in the registry record under "documentation").
    if doc:
        save_documentation(script_id, doc)

    add_changelog(script_meta, "初始版本")
    add_script(registry, script_meta)
    
    return f"✅ 自写脚本添加成功！\nID: {script_id}\n安装链接: {get_install_url(script_id)}"

def add_sync(registry: dict[str, Any], url: str) -> str:
    """按来源 URL 拉取并入库同步脚本（域名白名单 + 内容校验 + 重复检测）。

    同源的**软删条目走复活**（sync/update/rm 三处承诺的契约）：复用原 ID 就地
    清 deleted 并回写文件，而不是把它当重复添加拒绝；活跃条目仍然拒绝重复。"""
    existing = find_script_by_source_url(registry, url)
    if existing is not None and not existing.get("deleted"):
        return f"⚠️ 脚本已存在 (ID: {existing['id']}，来源: {url})，请勿重复添加。"

    adapter = get_adapter(url)
    if not adapter:
        return f"❌ 不支持的来源: {url}\n支持的来源: GreasyFork, Userscript.zone, GitHub Gist, 直接链接"

    try:
        source = adapter.fetch(url)
    except Exception as e:
        return f"❌ 从网页获取脚本失败: {e}"

    if "// ==UserScript==" not in source.code:
        return "❌ 获取的内容不是有效的油猴脚本（缺少 ==UserScript== 头部），已拒绝入库。"

    meta = source.meta
    # 头部字段（新旧两条路径共用；键序与历史 registry 保持一致，避免无谓 diff）
    head = {
        "type": "synced",
        "name": meta.get("name", "Unknown Script"),
        "version": meta.get("version", "1.0.0"),
        "description": meta.get("description", ""),
        "author": meta.get("author", ""),
        "namespace": meta.get("namespace", ""),
        "match": meta.get("match", ["*://*/*"]),
        "grant": meta.get("grant", ["none"]),
        "enabled": True,
        "source_url": url,
        "source_type": source.source_type,
    }
    tail = {
        "updated_at": now_iso(),
        "last_synced_at": now_iso(),
        "sync_enabled": True,
    }

    if existing is None:
        script_id = generate_synced_script_id(url)
        script_meta: dict[str, Any] = {"id": script_id, **head,
                                       "created_at": now_iso(),
                                       **tail, "documentation": ""}
    else:
        script_meta = existing          # 就地复活：保留 ID/created_at/changelog
        script_id = existing["id"]
        script_meta.update(head)
        script_meta.update(tail)
        script_meta["deleted"] = False

    # Write source file (original code unchanged)
    write_source_file(script_meta, source.code)

    # Build dist file with updated URLs only
    dist_code = build_dist_for_synced(script_meta, source.code)
    write_dist_file(script_id, dist_code)

    add_changelog(script_meta, "初始同步" if existing is None else "复活同步")
    if existing is not None:
        # 字段级就地修改：原地落盘，不追加重复条目
        save_registry(registry)
        return (f"✅ 同步脚本复活成功！\nID: {script_id}\n来源: {adapter.name}\n"
                f"安装链接: {get_install_url(script_id)}")
    add_script(registry, script_meta)

    return f"✅ 同步脚本添加成功！\nID: {script_id}\n来源: {adapter.name}\n安装链接: {get_install_url(script_id)}"