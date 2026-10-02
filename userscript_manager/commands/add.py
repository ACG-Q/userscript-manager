from ..config import CONFIG, get_install_url
from ..registry import add_script, find_script_by_source_url
from ..utils import (
    build_userscript_header, build_dist_for_synced, extract_meta_from_code,
    generate_self_script_id, generate_synced_script_id,
    write_dist_file, write_source_file, ensure_dirs, save_documentation, now_iso,
    add_changelog, format_js_code
)
from ..sources import get_adapter
from ..commands import register
from ..issue_parser import remove_code_blocks

@register("add")
def execute(registry, args, code, markdown, has_code_block):
    """/add [url]：带 URL 走同步添加，否则按代码块自写添加。"""
    ensure_dirs()
    if args:
        return add_sync(registry, args)
    else:
        return add_self(registry, code, markdown, has_code_block)

def add_self(registry, code, markdown, has_code_block):
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

def add_sync(registry, url):
    """按来源 URL 拉取并入库同步脚本（域名白名单 + 内容校验 + 重复检测）。"""
    existing = find_script_by_source_url(registry, url)
    if existing:
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
    
    script_id = generate_synced_script_id(url)
    
    meta = source.meta
    name = meta.get("name", "Unknown Script")
    
    script_meta = {
        "id": script_id,
        "type": "synced",
        "name": name,
        "version": meta.get("version", "1.0.0"),
        "description": meta.get("description", ""),
        "author": meta.get("author", ""),
        "namespace": meta.get("namespace", ""),
        "match": meta.get("match", ["*://*/*"]),
        "grant": meta.get("grant", ["none"]),
        "enabled": True,
        "source_url": url,
        "source_type": source.source_type,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "last_synced_at": now_iso(),
        "sync_enabled": True,
        "documentation": "",
    }
    
    # Write source file (original code unchanged)
    write_source_file(script_meta, source.code)
    
    # Build dist file with updated URLs only
    dist_code = build_dist_for_synced(script_meta, source.code)
    write_dist_file(script_id, dist_code)

    add_changelog(script_meta, "初始同步")
    add_script(registry, script_meta)
    
    return f"✅ 同步脚本添加成功！\nID: {script_id}\n来源: {adapter.name}\n安装链接: {get_install_url(script_id)}"