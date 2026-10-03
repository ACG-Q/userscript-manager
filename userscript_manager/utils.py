import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import jsbeautifier

from .config import CONFIG, get_install_url


def format_js_code(code: str) -> str:
    """统一美化 JS 源码（2 空格缩进、保留换行），自写脚本入库前调用。"""
    options = jsbeautifier.default_options()
    options.indent_size = 2
    options.indent_char = " "
    options.preserve_newlines = True
    options.jslint_happy = True
    options.end_with_newline = True
    return str(jsbeautifier.beautify(code, options))

def build_userscript_header(meta: dict[str, Any], code_body: str) -> str:
    """构建完整可安装脚本：有头部则保留原字段并同步 URL/版本，否则合成新头部。"""
    install_url = get_install_url(meta["id"])
    if "// ==UserScript==" in code_body:
        # 保留作者原头部的 @require/@run-at/@icon 等字段，只同步安装地址与版本
        code = ensure_userscript_urls(code_body, install_url)
        if meta.get("version"):
            code = sync_header_version(code, meta["version"])
        return code
    return _synthesize_header(meta, code_body)


def _synthesize_header(meta: dict[str, Any], code_body: str) -> str:
    name = meta.get("name", "Unnamed Script")
    namespace = meta.get("namespace", CONFIG["author"]["namespace"])
    version = meta.get("version", "1.0.0")
    description = meta.get("description", "")
    author = meta.get("author", CONFIG["author"]["name"])
    match = meta.get("match", ["*://*/*"])
    grant = meta.get("grant", ["none"])
    install_url = get_install_url(meta["id"])

    header = f"""// ==UserScript==
// @name         {name}
// @namespace    {namespace}
// @version      {version}
// @description  {description}
// @author       {author}
"""
    for m in match:
        header += f"// @match        {m}\n"
    for g in grant:
        header += f"// @grant        {g}\n"
    header += f"// @downloadURL  {install_url}\n"
    header += f"// @updateURL    {install_url}\n"
    header += "// ==/UserScript==\n\n"
    # Strip any existing UserScript header from code_body
    code_body = strip_header(code_body)
    return header + code_body

def extract_meta_from_code(code: str) -> dict[str, Any]:
    """从源码头部解析标量元数据与 @match/@grant 列表（共享解析器，勿复制）。"""
    meta = {}
    for key in ("name", "version", "description", "author", "namespace"):
        m = re.search(rf"// @{key}[ \t]+([^\n]+)", code)
        if m:
            meta[key] = m.group(1).strip()
    match_matches = re.findall(r"// @match[ \t]+([^\n]+)", code)
    if match_matches:
        meta["match"] = [m.strip() for m in match_matches]
    grant_matches = re.findall(r"// @grant[ \t]+([^\n]+)", code)
    if grant_matches:
        meta["grant"] = [g.strip() for g in grant_matches]
    return meta

def strip_header(code: str) -> str:
    """剥离 ==UserScript== 头部块，返回纯脚本体。"""
    lines = code.splitlines()
    inside = False
    body = []
    for line in lines:
        stripped = line.strip()
        if stripped == "// ==UserScript==":
            inside = True
            continue
        if inside and stripped == "// ==/UserScript==":
            inside = False
            continue
        if not inside:
            body.append(line)
    return "\n".join(body).strip()

def ensure_userscript_urls(code: str, install_url: str) -> str:
    """替换头部中的 @downloadURL/@updateURL，缺失时在头部末尾补入。

    除这两行与（可选的）@version 外，其余头部行原样保留。"""
    lines = code.splitlines()
    out = []
    has_download = False
    has_update = False
    close_idx = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("// @downloadURL"):
            out.append(f"// @downloadURL  {install_url}")
            has_download = True
        elif stripped.startswith("// @updateURL"):
            out.append(f"// @updateURL    {install_url}")
            has_update = True
        else:
            out.append(line)
        if stripped == "// ==/UserScript==":
            close_idx = len(out) - 1
    if not has_download or not has_update:
        additions = []
        if not has_download:
            additions.append(f"// @downloadURL  {install_url}")
        if not has_update:
            additions.append(f"// @updateURL    {install_url}")
        insert_at = close_idx if close_idx is not None else len(out)
        out[insert_at:insert_at] = additions
    return "\n".join(out)

def sync_header_version(code: str, version: str) -> str:
    """把头部 @version 行同步为 registry 中的版本；缺行则插入。"""
    lines = code.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("// @version"):
            lines[i] = f"// @version      {version}"
            return "\n".join(lines)
    for i, line in enumerate(lines):
        if line.strip() == "// ==/UserScript==":
            lines.insert(i, f"// @version      {version}")
            return "\n".join(lines)
    return "\n".join(lines)

def generate_self_script_id() -> str:
    """自写脚本 ID：UUID v4。"""
    return str(uuid.uuid4())

def generate_synced_script_id(source_url: str) -> str:
    """同步脚本 ID：来源 URL 的 MD5 前 12 位（同一 URL 天然去重）。"""
    return hashlib.md5(source_url.encode()).hexdigest()[:12]

def ensure_dirs() -> None:
    """按需创建源码与 dist 目录（幂等）。"""
    for d in [CONFIG["self_scripts_dir"], CONFIG["synced_scripts_dir"], CONFIG["dist_dir"]]:
        Path(d).mkdir(parents=True, exist_ok=True)

def write_dist_file(script_id: str, content: str) -> Path:
    """写入 dist/<id>.user.js 安装文件，返回路径。"""
    dist_file = Path(CONFIG["dist_dir"]) / f"{script_id}.user.js"
    dist_file.write_text(content, encoding="utf-8")
    return dist_file

def read_source_file(script: dict[str, Any]) -> str:
    """按脚本类型读取源码文件；不存在时返回空串。"""
    if script["type"] == "self":
        src_file = Path(CONFIG["self_scripts_dir"]) / script["id"] / "index.js"
    else:
        src_file = Path(CONFIG["synced_scripts_dir"]) / script["id"] / "script.user.js"
    return src_file.read_text(encoding="utf-8") if src_file.exists() else ""

def write_source_file(script: dict[str, Any], content: str) -> Path:
    """按脚本类型写入源码文件（self 用 index.js，synced 用 script.user.js）。"""
    sid = str(script["id"])  # 先收窄为 str：Path / Any 会让返回类型退化成 Any
    if script["type"] == "self":
        src_dir = Path(CONFIG["self_scripts_dir"]) / sid
        src_file = src_dir / "index.js"
    else:
        src_dir = Path(CONFIG["synced_scripts_dir"]) / sid
        src_file = src_dir / "script.user.js"
    src_dir.mkdir(parents=True, exist_ok=True)
    src_file.write_text(content, encoding="utf-8")
    return src_file

def remove_source_dir(script: dict[str, Any]) -> None:
    """删除脚本源码目录（不存在则忽略）。"""
    if script["type"] == "self":
        src_dir = Path(CONFIG["self_scripts_dir"]) / script["id"]
    else:
        src_dir = Path(CONFIG["synced_scripts_dir"]) / script["id"]
    if src_dir.exists():
        import shutil
        shutil.rmtree(src_dir)

def remove_dist_file(script_id: str) -> None:
    """删除对应 dist 安装文件（不存在则忽略）。"""
    dist_file = CONFIG["dist_dir"] / f"{script_id}.user.js"
    if dist_file.exists():
        dist_file.unlink()

def increment_version(version: str) -> str:
    """递增版本号：位数不足补 0，多段保留，非数字后缀原样跟随，绝不重置主版本。"""
    m = re.match(r"^(\d+(?:\.\d+)*)(.*)$", (version or "").strip())
    if not m:
        return "1.0.1"
    nums = [int(p) for p in m.group(1).split(".")]
    suffix = m.group(2)
    while len(nums) < 3:
        nums.append(0)
    nums[-1] += 1
    return ".".join(str(n) for n in nums) + suffix

def now_iso() -> str:
    """UTC ISO-8601 时间戳（Z 后缀）。"""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def add_changelog(script: dict[str, Any], note: str) -> None:
    """为脚本当前版本在 changelog 头部插入一行（原地修改）。"""
    script.setdefault("changelog", []).insert(0, {
        "version": script.get("version", ""),
        "date": now_iso()[:10],
        "note": note,
    })

def save_documentation(script_id: str, markdown: str) -> str:
    """把 Markdown 文档写入脚本源目录下的 README.md，返回相对项目根的路径。"""
    doc_file = CONFIG["self_scripts_dir"] / script_id / "README.md"
    doc_file.parent.mkdir(parents=True, exist_ok=True)
    doc_file.write_text(markdown, encoding="utf-8")
    return str(doc_file.relative_to(CONFIG["self_scripts_dir"].parent))


def build_dist_for_synced(script_meta: dict[str, Any], original_code: str) -> str:
    """Only update @downloadURL and @updateURL in the original code for synced scripts."""
    return ensure_userscript_urls(original_code, get_install_url(script_meta["id"]))