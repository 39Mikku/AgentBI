from __future__ import annotations

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup
from bs4.element import Tag


_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}
_TITLE_SUFFIX_PATTERN = re.compile(r"\s*[-–—]\s*萌娘百科\s*$")
_RLCONF_ASSIGNMENT_PATTERN = re.compile(r"\bRLCONF\s*=\s*")


class MoegirlValidationError(ValueError):
    pass


class MoegirlNotFoundError(RuntimeError):
    pass


class MoegirlUpstreamError(RuntimeError):
    pass


class MoegirlContentError(RuntimeError):
    pass


@dataclass(frozen=True)
class MoegirlPage:
    title: str
    source_url: str
    article_html: str
    categories: tuple[str, ...]


class MoegirlScraper:
    BASE_URL = "https://mzh.moegirl.org.cn/"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client

    async def fetch(self, name: str) -> MoegirlPage:
        normalized = name.strip()
        if not normalized or len(normalized) > 200:
            raise MoegirlValidationError("条目名称不能为空且不能超过 200 个字符")

        url = self.BASE_URL + quote(normalized, safe="")
        try:
            if self.client is not None:
                response = await self.client.get(
                    url,
                    headers=_REQUEST_HEADERS,
                    follow_redirects=True,
                    timeout=30,
                )
            else:
                async with httpx.AsyncClient(
                    headers=_REQUEST_HEADERS,
                    follow_redirects=True,
                    timeout=30,
                ) as client:
                    response = await client.get(url)
            if response.status_code == 404:
                raise MoegirlNotFoundError(f"萌娘百科条目不存在：{normalized}")
            response.raise_for_status()
        except MoegirlNotFoundError:
            raise
        except httpx.HTTPError as exc:
            raise MoegirlUpstreamError("萌娘百科请求失败") from exc

        return self.extract(response.text, str(response.url))

    @staticmethod
    def extract(response_html: str, source_url: str) -> MoegirlPage:
        soup = BeautifulSoup(response_html, "html.parser")
        content_soup = soup
        template = soup.select_one("template#MOE_SKIN_TEMPLATE_BODYCONTENT")
        if template is not None:
            content_soup = BeautifulSoup(template.decode_contents(), "html.parser")

        article = _find_article(content_soup)
        if content_soup is not soup and not _has_article_content(article):
            article = _find_article(soup)

        config = _extract_rlconf(soup)
        title = _config_title(config) or _fallback_title(soup)
        categories = _config_categories(config) or _fallback_categories(soup)
        if not title or not _has_article_content(article):
            raise MoegirlContentError("萌娘百科页面缺少标题或正文内容")

        return MoegirlPage(
            title=title,
            source_url=source_url,
            article_html=str(article),
            categories=categories,
        )


def _extract_rlconf(soup: BeautifulSoup) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for script in soup.find_all("script"):
        script_text = script.string or script.get_text()
        match = _RLCONF_ASSIGNMENT_PATTERN.search(script_text)
        if match is None:
            continue
        try:
            value, _ = decoder.raw_decode(script_text, match.end())
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            return value
    return {}


def _find_article(soup: BeautifulSoup) -> Tag | None:
    for selector in (
        "#mw-content-text",
        ".mw-parser-output",
        ".mw-body-content",
        "article",
        "main",
    ):
        article = soup.select_one(selector)
        if article is not None:
            return article
    return None


def _has_article_content(article: Tag | None) -> bool:
    return article is not None and bool(article.get_text(" ", strip=True))


def _config_title(config: dict[str, Any]) -> str:
    title = config.get("wgPageName")
    return title.strip() if isinstance(title, str) else ""


def _config_categories(config: dict[str, Any]) -> tuple[str, ...]:
    categories = config.get("wgCategories")
    if not isinstance(categories, list):
        return ()
    return _unique_nonempty(category for category in categories if isinstance(category, str))


def _fallback_title(soup: BeautifulSoup) -> str:
    for selector in ("#firstHeading", "h1", "title"):
        element = soup.select_one(selector)
        if element is None:
            continue
        title = element.get_text(" ", strip=True)
        if selector == "title":
            title = _TITLE_SUFFIX_PATTERN.sub("", title)
        if title:
            return title
    return ""


def _fallback_categories(soup: BeautifulSoup) -> tuple[str, ...]:
    links = soup.select('a[href*="Category:"]')
    return _unique_nonempty(link.get_text(" ", strip=True) for link in links)


def _unique_nonempty(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
