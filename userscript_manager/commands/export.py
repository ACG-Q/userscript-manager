import json
from typing import Any

from ..commands import register
from ..config import get_install_url


@register("export")
def execute(registry: dict[str, Any], args: str, code: str,
            markdown: str, has_code_block: bool) -> str:
    """/export [md|json]：导出脚本清单，默认 Markdown 表格。"""
    visible = [s for s in registry["scripts"] if not s.get("deleted")]
    if not visible:
        return "📭 当前没有脚本。"

    format_type = args.lower() if args else "md"

    if format_type == "json":
        return export_json(visible)
    else:
        return export_markdown(visible)

def export_markdown(scripts: list[dict[str, Any]]) -> str:
    """渲染 Markdown 安装列表（状态/类型/ID/名称/版本/链接）。"""
    lines = [
        "# 油猴脚本安装列表",
        "",
        "| 状态 | 类型 | ID | 名称 | 版本 | 安装链接 |",
        "|------|------|----|------|------|----------|",
    ]

    for s in scripts:
        status = "✅" if s.get("enabled", True) else "⏸️"
        script_type = "📝" if s["type"] == "self" else "🔄"
        install_url = get_install_url(s['id'])
        lines.append(
            f"| {status} | {script_type} | {s['id']} | {s['name']} | "
            f"v{s['version']} | [安装]({install_url}) |"
        )
    
    return "\n".join(lines)

def export_json(scripts: list[dict[str, Any]]) -> str:
    """导出 JSON 清单（含安装链接，便于外部消费）。"""
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
            for s in scripts
        ]
    }
    return json.dumps(export_data, indent=2, ensure_ascii=False)