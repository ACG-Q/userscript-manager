from urllib.parse import urlparse

from .base import BaseSourceAdapter, ScriptSource, http_get

class DirectUrlAdapter(BaseSourceAdapter):
    """Handle direct raw script URLs (raw.githubusercontent.com, github.com/.../raw/..., etc.)"""

    @property
    def name(self) -> str:
        return "Direct URL"

    @property
    def domains(self) -> list[str]:
        return [
            "raw.githubusercontent.com",
            "raw.githack.com",
            "cdn.jsdelivr.net",
            "gitcdn.xyz",
        ]

    def matches(self, url: str) -> bool:
        """除精确域名外，额外接受 github.com 的 /raw/ 直链（302 到 raw.githubusercontent.com）。"""
        if super().matches(url):
            return True
        try:
            parsed = urlparse(url)
        except ValueError:
            return False
        return (parsed.hostname or "").lower() == "github.com" and "/raw/" in parsed.path

    def fetch(self, url: str) -> ScriptSource:
        resp = http_get(url)
        resp.raise_for_status()

        raw_code = resp.text
        meta = self._extract_meta(raw_code)

        # Try to determine source type from URL
        source_type = "direct"
        if "github" in url:
            source_type = "github_raw"
        elif "githack" in url:
            source_type = "githack"
        elif "jsdelivr" in url:
            source_type = "jsdelivr"

        return ScriptSource(
            code=raw_code,
            meta=meta,
            source_url=url,
            source_type=source_type
        )
