import re
from typing import Any

from .base import BaseSourceAdapter, ScriptSource, http_get


def pick_gist_file(files: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """从 gist API 的 files 字典挑选最可能的脚本文件：.user.js > .js > 首个。"""
    if not files:
        return "", {}
    for name in sorted(files):
        if name.endswith(".user.js"):
            return name, files[name]
    for name in sorted(files):
        if name.endswith(".js"):
            return name, files[name]
    name = next(iter(files))
    return name, files[name]


class GitHubGistAdapter(BaseSourceAdapter):
    """GitHub Gist 来源适配器。"""
    @property
    def name(self) -> str:
        """适配器展示名。"""
        return "GitHub Gist"

    @property
    def domains(self) -> list[str]:
        """允许的精确域名列表（含子域）。"""
        return ["gist.github.com", "gist.githubusercontent.com"]

    def fetch(self, url: str) -> ScriptSource:
        """抓取并解析脚本内容，返回 ScriptSource。"""
        raw_code = None
        raw_url = self._to_raw_url(url)

        # 页面型 URL（gist.github.com/...）可能包含多文件，必须走 API 选文件；
        # 直接 raw 地址则原样抓取。
        if "gist.github.com" in url:
            gist_id = self._extract_gist_id(url)
            if gist_id:
                api_url = f"https://api.github.com/gists/{gist_id}"
                api_resp = http_get(api_url)
                api_resp.raise_for_status()
                _name, info = pick_gist_file(api_resp.json().get("files", {}))
                content = (info or {}).get("content") or ""
                if content:
                    raw_code = content
                    raw_url = info.get("raw_url", raw_url)

        if raw_code is None:
            resp = http_get(raw_url)
            resp.raise_for_status()
            raw_code = resp.text

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