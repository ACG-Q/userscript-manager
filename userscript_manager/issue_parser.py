import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class ParsedComment:
    """一条评论的解析结果：命令、参数、Markdown 正文与首个代码块。"""
    command: Optional[str]
    args: str
    markdown: str          # Full markdown body (for documentation)
    code: str              # Extracted code from first code block (for script)
    has_code_block: bool   # Whether a code block was found

def parse_comment(comment_body: str) -> ParsedComment:
    """
    Parse issue comment with Markdown support.
    
    Format:
    /command [args]
    [markdown content with code blocks]
    
    Returns ParsedComment with:
    - command: command name (without /)
    - args: arguments after command
    - markdown: full markdown body (for docs/description)
    - code: code extracted from first fenced code block (for script)
    - has_code_block: whether a code block was found
    """
    lines = comment_body.strip().splitlines()
    if not lines:
        return ParsedComment(None, "", "", "", False)

    first_line = lines[0].strip()
    rest_lines = lines[1:] if len(lines) > 1 else []

    match = re.match(r"^\s*/([a-zA-Z0-9_-]+)(?:\s+(.+))?$", first_line)
    if not match:
        return ParsedComment(None, "", "", "", False)

    cmd = match.group(1).lower()
    args = match.group(2) if match.group(2) else ""

    markdown = "\n".join(rest_lines).strip()
    code, has_code_block = extract_first_code_block(markdown)

    return ParsedComment(
        command=cmd,
        args=args,
        markdown=markdown,
        code=code,
        has_code_block=has_code_block
    )

_FENCE_RE = re.compile(r"```(?:[a-zA-Z0-9_+-]+)?\s*\n(.*?)\n```", re.DOTALL)

def extract_first_code_block(markdown: str) -> tuple[str, bool]:
    """Extract code from first fenced code block (```lang ... ```)."""
    match = _FENCE_RE.search(markdown)
    if match:
        return match.group(1).strip(), True
    return "", False

def extract_all_code_blocks(markdown: str) -> list[str]:
    """Extract all fenced code blocks."""
    return [m.group(1).strip() for m in _FENCE_RE.finditer(markdown)]

def remove_code_blocks(markdown: str) -> str:
    """Return markdown with all fenced code blocks stripped (prose only)."""
    return _FENCE_RE.sub("", markdown).strip()

# Backward compatibility
def clean_code_block(text: str) -> str:
    """Legacy: extract first code block or return original."""
    code, _ = extract_first_code_block(text)
    return code if code else text