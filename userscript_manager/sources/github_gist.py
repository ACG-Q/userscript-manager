import re
import requests
from .base import BaseSourceAdapter, ScriptSource

class GitHubGistAdapter(BaseSourceAdapter):
    @property
    def name(self) -> str:
        return "GitHub Gist"

    @property
    def domains(self) -> list[str]:
        return ["gist.github.com", "gist.githubusercontent.com"]

    def fetch(self, url: str) -> ScriptSource:
        # Convert to raw URL if needed
        raw_url = self._to_raw_url(url)
        
        resp = requests.get(raw_url, timeout=15)
        resp.raise_for_status()
        
        raw_code = resp.text
        
        # If it's a gist with multiple files, find the .user.js file
        if raw_url.endswith(".json") or "gist.github.com" in raw_url:
            # This is the gist page, not raw content
            # We need to parse the gist API
            gist_id = self._extract_gist_id(url)
            if gist_id:
                api_url = f"https://api.github.com/gists/{gist_id}"
                api_resp = requests.get(api_url, timeout=15)
                api_resp.raise_for_status()
                gist_data = api_resp.json()
                
                # Find the .user.js file
                for filename, file_info in gist_data.get("files", {}).items():
                    if filename.endswith(".user.js") or filename.endswith(".js"):
                        raw_code = file_info.get("content", "")
                        raw_url = file_info.get("raw_url", raw_url)
                        break
        
        meta = self._extract_meta(raw_code)
        
        return ScriptSource(
            code=raw_code,
            meta=meta,
            source_url=url,
            source_type="github_gist"
        )
    
    def _to_raw_url(self, url: str) -> str:
        # gist.github.com/user/id -> gist.githubusercontent.com/user/id/raw
        # gist.github.com/id -> gist.githubusercontent.com/id/raw
        if "gist.githubusercontent.com" in url:
            return url
        if "gist.github.com" in url:
            return url.replace("gist.github.com", "gist.githubusercontent.com") + "/raw"
        return url
    
    def _extract_gist_id(self, url: str) -> str | None:
        match = re.search(r"gist\.github\.com/(?:[^/]+/)?([a-f0-9]+)", url)
        return match.group(1) if match else None

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