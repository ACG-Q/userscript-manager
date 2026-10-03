from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import urlparse

import requests

from ..utils import extract_meta_from_code

BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def http_get(url: str, timeout: int = 15) -> requests.Response:
    """带浏览器请求头的 GET：默认 python-requests UA 会被 GreasyFork 等站点 403 拦截。"""
    return requests.get(url, timeout=timeout, headers=BROWSER_HEADERS)

@dataclass
class ScriptSource:
    """Parsed script from a source."""
    code: str              # Raw script code (with header)
    meta: dict[str, Any]   # Extracted metadata
    source_url: str        # Original URL
    source_type: str       # e.g., "greasyfork", "userscript_zone", "github_gist", "direct"

class BaseSourceAdapter(ABC):
    """Base class for source adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name."""

    @property
    @abstractmethod
    def domains(self) -> list[str]:
        """List of domains this adapter handles."""

    def matches(self, url: str) -> bool:
        """按 hostname 精确/子域匹配，防止 evil.com/path/greasyfork.org 绕过。"""
        try:
            host = urlparse(url).hostname or ""
        except ValueError:
            return False
        host = host.lower()
        return any(host == d or host.endswith("." + d) for d in self.domains)

    def _extract_meta(self, code: str) -> dict[str, Any]:
        """共享元数据解析器，适配器不再各自复制实现。"""
        return extract_meta_from_code(code)

    @abstractmethod
    def fetch(self, url: str) -> ScriptSource:
        """Fetch script from URL, return parsed source."""
        pass

_adapters: list[BaseSourceAdapter] = []

def register_adapter(adapter: BaseSourceAdapter) -> None:
    """把适配器实例注册进全局表。"""
    _adapters.append(adapter)

def get_adapter(url: str) -> Optional[BaseSourceAdapter]:
    """按精确域名匹配返回适配器；无匹配返回 None。"""
    for adapter in _adapters:
        if adapter.matches(url):
            return adapter
    return None

def get_all_adapters() -> list[BaseSourceAdapter]:
    """返回全部已注册适配器的副本（供枚举/文档使用）。"""
    return _adapters.copy()