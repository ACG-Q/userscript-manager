import re
import requests
from bs4 import BeautifulSoup
from .base import BaseSourceAdapter, ScriptSource

class GreasyForkAdapter(BaseSourceAdapter):
    @property
    def name(self) -> str:
        return "GreasyFork"

    @property
    def domains(self) -> list[str]:
        return ["greasyfork.org"]

    def fetch(self, url: str) -> ScriptSource:
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

    def _extract_meta(self, code: str) -> dict:
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