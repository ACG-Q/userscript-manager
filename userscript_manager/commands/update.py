from ..config import get_install_url
from ..registry import save_registry, find_script
from ..utils import (
    build_userscript_header, extract_meta_from_code, increment_version,
    write_dist_file, write_source_file, save_documentation, now_iso,
    add_changelog
)
from ..commands import register
from ..issue_parser import remove_code_blocks

@register("up")
def execute(registry, args, code, markdown, has_code_block):
    """/up <id>：用新代码块更新脚本，版本自增并记录 changelog。"""
    if not args:
        return "❌ 请提供要更新的脚本 ID，例如 /up <script_id>"
    if not has_code_block or not code.strip():
        return "❌ 请提供新的脚本代码（在 Markdown 代码块中）。"
    
    script = find_script(registry, args)
    if not script:
        return f"❌ 未找到 ID 为 {args} 的脚本。"
    if script["type"] != "self":
        return f"❌ ID {args} 不是自写脚本，无法更新。同步脚本请使用 /sync {args}"
    
    meta = extract_meta_from_code(code)
    
    # Update script metadata from new code
    script["name"] = meta.get("name", script["name"])
    script["version"] = increment_version(script["version"])
    script["description"] = meta.get("description", script["description"])
    script["author"] = meta.get("author", script["author"])
    script["namespace"] = meta.get("namespace", script["namespace"])
    script["match"] = meta.get("match", script["match"])
    script["grant"] = meta.get("grant", script["grant"])
    script["updated_at"] = now_iso()
    add_changelog(script, "手动更新")
    
    write_source_file(script, code)
    
    full_code = build_userscript_header(script, code)
    write_dist_file(args, full_code)
    
    # Only touch documentation when the comment carries real prose; a
    # code-only update must keep the existing docs (C1).
    doc = markdown if remove_code_blocks(markdown).strip() else ""
    if doc:
        script["documentation"] = doc
        save_documentation(args, doc)
    
    save_registry(registry)
    
    return f"✅ 脚本 {args} 更新成功！新版本 {script['version']}\n安装链接: {get_install_url(args)}"