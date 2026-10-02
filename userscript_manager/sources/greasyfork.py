import requests
from bs4 import BeautifulSoup
from .base import BaseSourceAdapter, ScriptSource

class GreasyForkAdapter(BaseSourceAdapter):
    """GreasyFork 来源适配器。"""
    @property
    def name(self) -> str:
        """适配器展示名。"""
        return "GreasyFork"

    @property
    def domains(self) -> list[str]:
        """允许的精确域名列表（含子域）。"""
        return ["greasyfork.org"]

    def fetch(self, url: str) -> ScriptSource:
        """抓取并解析脚本内容，返回 ScriptSource。"""
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to find code in various locations
        code_elem = soup.find("pre", class_="code")
        if not code_elem:
            code_elem = soup.find("code")
        if not code_elem:
            # Try script-show-source
            code_elem = soup.find("div", class_="script-show-source")
        if not code_elem:
            raise ValueError("Cannot find script code on page")

        raw_code = code_elem.get_text()

        # Extract metadata from code
        meta = self._extract_meta(raw_code)

        # Determine source type more specifically
        source_type = "greasyfork"

        return ScriptSource(
            code=raw_code,
            meta=meta,
            source_url=url,
            source_type=source_type
        )