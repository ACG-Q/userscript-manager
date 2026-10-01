import json
from ..registry import load_registry
from ..config import get_install_url
from ..commands import register

@register("export")
def execute(registry, args, code, markdown, has_code_block):
    if not registry["scripts"]:
        return "📭 当前没有脚本。"
    
    format_type = args.lower() if args else "md"
    
    if format_type == "json":
        return export_json(registry)
    else:
        return export_markdown(registry)

def export_markdown(registry):
    lines = ["# 油猴脚本安装列表", "", "| 状态 | 类型 | ID | 名称 | 版本 | 安装链接 |", "|------|------|----|------|------|----------|"]
    
    for s in registry["scripts"]:
        status = "✅" if s.get("enabled", True) else "⏸️"
        script_type = "📝" if s["type"] == "self" else "🔄"
        install_url = get_install_url(s['id'])
        lines.append(f"| {status} | {script_type} | {s['id']} | {s['name']} | v{s['version']} | [安装]({install_url}) |")
    
    return "\n".join(lines)

def export_json(registry):
    export_data = {
        "scripts": [
            {
                "id": s["id"],
                "type": s["type"],
                "name": s["name"],
                "version": s["version"],
                "enabled": s.get("enabled", True),
                "install_url": get_install_url(s['id']),
            }
            for s in registry["scripts"]
        ]
    }
    return json.dumps(export_data, indent=2, ensure_ascii=False)