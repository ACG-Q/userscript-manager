import requests
from bs4 import BeautifulSoup
from .base import BaseSourceAdapter, ScriptSource

class UserscriptZoneAdapter(BaseSourceAdapter):
    """Userscript.zone 来源适配器。"""
    @property
    def name(self) -> str:
        """适配器展示名。"""
        return "Userscript.zone"

    @property
    def domains(self) -> list[str]:
        """允许的精确域名列表（含子域）。"""
        return ["userscript.zone"]

    def fetch(self, url: str) -> ScriptSource:
        """抓取并解析脚本内容，返回 ScriptSource。"""
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Userscript.zone has raw code in a pre/code block
        code_elem = soup.find("pre", class_="language-javascript")
        if not code_elem:
            code_elem = soup.find("code")
        if not code_elem:
            # Try to find the script content
            code_elem = soup.find("div", class_="script-source")
        if not code_elem:
            raise ValueError("Cannot find script code on page")

        raw_code = code_elem.get_text()

        meta = self._extract_meta(raw_code)

        return ScriptSource(
            code=raw_code,
            meta=meta,
            source_url=url,
            source_type="userscript_zone"
        )