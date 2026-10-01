import re
import hashlib
import uuid
import jsbeautifier
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .config import CONFIG, get_install_url

def format_js_code(code: str) -> str:
    options = jsbeautifier.default_options()
    options.indent_size = 2
    options.indent_char = " "
    options.preserve_newlines = True
    options.jslint_happy = True
    options.end_with_newline = True
    return jsbeautifier.beautify(code, options)

def build_userscript_header(meta: dict, code_body: str) -> str:
    install_url = get_install_url(meta["id"])
    if "// ==UserScript==" in code_body:
        # 保留作者原头部的 @require/@run-at/@icon 等字段，只同步安装地址与版本
        code = ensure_userscript_urls(code_body, install_url)
        if meta.get("version"):
            code = sync_header_version(code, meta["version"])
        return code
    return _synthesize_header(meta, code_body)


def _synthesize_header(meta: dict, code_body: str) -> str:
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

def extract_meta_from_code(code: str) -> dict:
    meta = {}
    patterns = {
        "name": r"// @name\s+(.+?)\n",
        "version": r"// @version\s+(.+?)\n",
        "description": r"// @description\s+(.+?)\n",
        "author": r"// @author\s+(.+?)\n",
        "namespace": r"// @namespace\s+(.+?)\n",
    }
    for key, pattern in patterns.items():
        m = re.search(pattern, code)
        if m:
            meta[key] = m.group(1).strip()
    match_matches = re.findall(r"// @match\s+(.+?)\n", code)
    if match_matches:
        meta["match"] = [m.strip() for m in match_matches]
    grant_matches = re.findall(r"// @grant\s+(.+?)\n", code)
    if grant_matches:
        meta["grant"] = [g.strip() for g in grant_matches]
    return meta

def strip_header(code: str) -> str:
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
    return str(uuid.uuid4())

def generate_synced_script_id(source_url: str) -> str:
    return hashlib.md5(source_url.encode()).hexdigest()[:12]

def ensure_dirs() -> None:
    for d in [CONFIG["self_scripts_dir"], CONFIG["synced_scripts_dir"], CONFIG["dist_dir"]]:
        Path(d).mkdir(parents=True, exist_ok=True)

def write_dist_file(script_id: str, content: str) -> Path:
    dist_file = CONFIG["dist_dir"] / f"{script_id}.user.js"
    dist_file.write_text(content, encoding="utf-8")
    return dist_file

def read_source_file(script: dict) -> str:
    if script["type"] == "self":
        src_file = CONFIG["self_scripts_dir"] / script["id"] / "index.js"
    else:
        src_file = CONFIG["synced_scripts_dir"] / script["id"] / "script.user.js"
    return src_file.read_text(encoding="utf-8") if src_file.exists() else ""

def write_source_file(script: dict, content: str) -> Path:
    if script["type"] == "self":
        src_dir = CONFIG["self_scripts_dir"] / script["id"]
        src_file = src_dir / "index.js"
    else:
        src_dir = CONFIG["synced_scripts_dir"] / script["id"]
        src_file = src_dir / "script.user.js"
    src_dir.mkdir(parents=True, exist_ok=True)
    src_file.write_text(content, encoding="utf-8")
    return src_file

def remove_source_dir(script: dict) -> None:
    if script["type"] == "self":
        src_dir = CONFIG["self_scripts_dir"] / script["id"]
    else:
        src_dir = CONFIG["synced_scripts_dir"] / script["id"]
    if src_dir.exists():
        import shutil
        shutil.rmtree(src_dir)

def remove_dist_file(script_id: str) -> None:
    dist_file = CONFIG["dist_dir"] / f"{script_id}.user.js"
    if dist_file.exists():
        dist_file.unlink()

def increment_version(version: str) -> str:
    parts = version.split(".")
    try:
        major, minor, patch = map(int, parts[:3])
    except ValueError:
        major, minor, patch = 1, 0, 0
    patch += 1
    return f"{major}.{minor}.{patch}"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def add_changelog(script: dict, note: str) -> None:
    """为脚本当前版本在 changelog 头部插入一行（原地修改）。"""
    script.setdefault("changelog", []).insert(0, {
        "version": script.get("version", ""),
        "date": now_iso()[:10],
        "note": note,
    })

def save_documentation(script_id: str, markdown: str) -> None:
    """Write markdown documentation for a script under its source dir.

    Returns the path of the written README.md (relative to project root) so the
    caller can store it in the in-memory registry without an extra load/save.
    """
    doc_file = CONFIG["self_scripts_dir"] / script_id / "README.md"
    doc_file.parent.mkdir(parents=True, exist_ok=True)
    doc_file.write_text(markdown, encoding="utf-8")
    return str(doc_file.relative_to(CONFIG["self_scripts_dir"].parent))


def build_dist_for_synced(script_meta: dict, original_code: str) -> str:
    """Only update @downloadURL and @updateURL in the original code for synced scripts."""
    return ensure_userscript_urls(original_code, get_install_url(script_meta["id"]))