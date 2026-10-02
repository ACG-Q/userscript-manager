from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from ..utils import extract_meta_from_code

@dataclass
class ScriptSource:
    """Parsed script from a source."""
    code: str              # Raw script code (with header)
    meta: dict             # Extracted metadata
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

    def _extract_meta(self, code: str) -> dict:
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