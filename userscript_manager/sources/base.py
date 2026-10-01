from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

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
        return any(domain in url for domain in self.domains)

    @abstractmethod
    def fetch(self, url: str) -> ScriptSource:
        """Fetch script from URL, return parsed source."""
        pass

_adapters: list[BaseSourceAdapter] = []

def register_adapter(adapter: BaseSourceAdapter) -> None:
    _adapters.append(adapter)

def get_adapter(url: str) -> Optional[BaseSourceAdapter]:
    for adapter in _adapters:
        if adapter.matches(url):
            return adapter
    return None

def get_all_adapters() -> list[BaseSourceAdapter]:
    return _adapters.copy()