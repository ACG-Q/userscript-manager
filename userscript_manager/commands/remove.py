from ..config import CONFIG
from ..registry import load_registry, save_registry, find_script, find_script_by_source_url
from ..utils import remove_source_dir, remove_dist_file
from ..commands import register

@register("rm")
def execute(registry, args, code, markdown, has_code_block):
    if not args:
        return "❌ 请提供要删除的 URL 或 ID，例如 /rm <url> 或 /rm <script_id>"
    
    if args.startswith("http://") or args.startswith("https://"):
        return remove_by_url(registry, args)
    else:
        return remove_by_id(registry, args)

def remove_by_url(registry, url):
    script = find_script_by_source_url(registry, url)
    if not script:
        return f"❌ 未找到来源为 {url} 的脚本。"
    
    remove_source_dir(script)
    remove_dist_file(script["id"])
    
    registry["scripts"] = [s for s in registry["scripts"] if s["id"] != script["id"]]
    save_registry(registry)
    return f"🗑️ 已删除同步脚本 {script['id']}（来源 {url}）"

def remove_by_id(registry, script_id):
    script = find_script(registry, script_id)
    if not script:
        return f"❌ 未找到 ID 为 {script_id} 的脚本。"
    
    remove_source_dir(script)
    remove_dist_file(script_id)
    
    registry["scripts"] = [s for s in registry["scripts"] if s["id"] != script_id]
    save_registry(registry)
    return f"🗑️ 已删除脚本 {script_id}"