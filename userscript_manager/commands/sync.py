from ..registry import save_registry, find_script
from ..utils import (
    build_dist_for_synced, write_dist_file, write_source_file,
    read_source_file, now_iso, add_changelog
)
from ..sources import get_adapter
from ..commands import register

@register("sync")
def execute(registry, args, code, markdown, has_code_block):
    """/sync <id>：立即拉取该同步脚本的最新版本并落盘。"""
    if not args:
        return "❌ 请提供要同步的脚本 ID，例如 /sync <script_id>"
    
    script = find_script(registry, args)
    if not script:
        return f"❌ 未找到 ID 为 {args} 的脚本。"
    if script["type"] != "synced":
        return f"❌ ID {args} 不是同步脚本，无法同步。"
    
    result = sync_script(registry, script)
    save_registry(registry)
    return result

@register("sync-all")
def execute_sync_all(registry, args, code, markdown, has_code_block):
    """/sync-all：批量同步全部启用自动同步的脚本（单个失败不阻断其余）。"""
    synced_scripts = [
        s for s in registry["scripts"]
        if s["type"] == "synced" and s.get("sync_enabled", True)
    ]
    if not synced_scripts:
        return "📭 没有启用自动同步的脚本。"
    
    results = []
    for script in synced_scripts:
        try:
            result = sync_script(registry, script)
            results.append(f"  ✅ {script['id']} ({script['name']}): {result}")
        except Exception as e:
            results.append(f"  ❌ {script['id']} ({script['name']}): {e}")
    
    save_registry(registry)
    return "🔄 批量同步完成：\n" + "\n".join(results)

def sync_script(registry, script):
    """执行单个脚本的同步：拉取→版本校验→写源码/dist→更新记录。"""
    url = script.get("source_url")
    if not url:
        return "❌ 缺少源 URL"
    
    adapter = get_adapter(url)
    if not adapter:
        return f"❌ 不支持的来源类型: {script.get('source_type')}"
    
    try:
        source = adapter.fetch(url)
    except Exception as e:
        return f"❌ 获取失败: {e}"

    if "// ==UserScript==" not in source.code:
        return "❌ 获取的内容不是有效的油猴脚本（缺少 ==UserScript== 头部），已跳过同步"
    
    # Check if code actually changed
    old_code = read_source_file(script)
    if old_code.strip() == source.code.strip():
        script["last_synced_at"] = now_iso()
        return "无变化"
    
    # Update source file
    write_source_file(script, source.code)
    
    # Update metadata from source (version, description, etc.)
    meta = source.meta
    old_version = script["version"]
    script["version"] = meta.get("version", script["version"])
    if script["version"] != old_version:
        add_changelog(script, "上游同步")
    script["description"] = meta.get("description", script["description"])
    script["author"] = meta.get("author", script["author"])
    script["namespace"] = meta.get("namespace", script["namespace"])
    script["match"] = meta.get("match", script["match"])
    script["grant"] = meta.get("grant", script["grant"])
    script["updated_at"] = now_iso()
    script["last_synced_at"] = now_iso()
    
    # Rebuild dist with updated URLs
    dist_code = build_dist_for_synced(script, source.code)
    write_dist_file(script["id"], dist_code)
    
    return f"已更新到 v{script['version']}"