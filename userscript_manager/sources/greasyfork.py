import re
from urllib.parse import urlparse, urlunparse

import requests
from bs4 import BeautifulSoup

from .base import BaseSourceAdapter, ScriptSource, http_get

_INSTALL_LINK_RE = re.compile(r"^https://update\.greasyfork\.org/")
_SCRIPT_ID_RE = re.compile(r"/scripts/(\d+)")

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
        """优先 update 子域按 ID 直取源码，失败回退页面链；全失败给出各入口状态。"""
        attempts: list[str] = []
        raw_code = self._download_by_id(url, attempts)
        if not self._is_script(raw_code):
            raw_code = self._fetch_from_page(url, attempts)
        if not self._is_script(raw_code):
            raise ValueError("所有入口均失败: " + "; ".join(attempts))

        return ScriptSource(
            code=raw_code,
            meta=self._extract_meta(raw_code),
            source_url=url,
            source_type="greasyfork",
        )

    @staticmethod
    def _safe_get(url: str, attempts: list[str], label: str) -> str:
        """带标签的容错 GET：成功返回正文，失败记入 attempts 并返回空串。"""
        try:
            resp = http_get(url)
            resp.raise_for_status()
        except requests.RequestException as e:
            status = e.response.status_code if e.response is not None else type(e).__name__
            attempts.append(f"{label} {status}")
            return ""
        return resp.text

    def _download_by_id(self, url: str, attempts: list[str]) -> str:
        """update 子域按脚本 ID 直取原始代码（绕过主站页面，生产由 nginx 直出）。"""
        match = _SCRIPT_ID_RE.search(urlparse(url).path)
        if not match:
            attempts.append("update直链 URL无脚本ID")
            return ""
        return self._safe_get(
            f"https://update.greasyfork.org/scripts/{match.group(1)}.user.js",
            attempts,
            "update直链",
        )

    def _fetch_from_page(self, url: str, attempts: list[str]) -> str:
        """页面链回退：内嵌源码 → 安装直链 → /code 页，逐级容错。"""
        html = self._safe_get(url, attempts, "主页")
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")

        code = self._code_from_elements(soup)
        if self._is_script(code):
            return code

        link = soup.find("a", href=_INSTALL_LINK_RE)
        href = link["href"] if link is not None else None
        if isinstance(href, str):
            code = self._safe_get(href, attempts, "安装直链")
            if self._is_script(code):
                return code

        return self._download_code_page(url, attempts)

    def _download_code_page(self, url: str, attempts: list[str]) -> str:
        """回退抓取 /code 页并解析其代码块。"""
        parsed = urlparse(url)
        if parsed.path.rstrip("/").endswith("/code"):
            attempts.append("code页 目标已是code页")
            return ""
        code_url = urlunparse(parsed._replace(
            path=parsed.path.rstrip("/") + "/code", query="", fragment="",
        ))
        html = self._safe_get(code_url, attempts, "code页")
        if not html:
            return ""
        soup = BeautifulSoup(html, "html.parser")
        elem = (
            soup.find("pre", class_="prettyprint")
            or soup.find("pre", class_="code")
            or soup.find("pre")
        )
        if not elem:
            attempts.append("code页 无代码块")
            return ""
        return elem.get_text()

    def _code_from_elements(self, soup: BeautifulSoup) -> str:
        """从页面内嵌代码块取源码（历史结构 pre.code 与现行 prettyprint）。"""
        elem = (
            soup.find("pre", class_="code")
            or soup.find("pre", class_="prettyprint")
            or soup.find("code")
            or soup.find("div", class_="script-show-source")
        )
        return elem.get_text() if elem else ""

    @staticmethod
    def _is_script(code: str) -> bool:
        """与 add/sync 层的内容校验保持同一判据。"""
        return bool(code) and "// ==UserScript==" in code
