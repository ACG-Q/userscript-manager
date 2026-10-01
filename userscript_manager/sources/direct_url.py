import re
import requests
from .base import BaseSourceAdapter, ScriptSource

class DirectUrlAdapter(BaseSourceAdapter):
    """Handle direct raw script URLs (raw.githubusercontent.com, raw.githack.com, etc.)"""
    
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
    
    def fetch(self, url: str) -> ScriptSource:
        resp = requests.get(url, timeout=15)
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