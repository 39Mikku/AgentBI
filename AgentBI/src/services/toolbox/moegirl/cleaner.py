from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

import html2text
from bs4 import BeautifulSoup

from AgentBI.src.services.toolbox.moegirl.scraper import MoegirlPage


_NOISE_SELECTORS = (
    "script",
    "style",
    "nav",
    "footer",
    "img",
    ".mw-editsection",
    ".reference",
    ".references",
    ".mw-references-wrap",
    ".reflist",
    "#references",
    "#References",
    ".navbox",
    ".vertical-navbox",
    ".navigation-not-searchable",
)
_RAW_URL_PATTERN = re.compile(
    r"https?://[A-Za-z0-9._~:/?#@!$&'*+,;=%-]+"
    r"(?:\([A-Za-z0-9._~:/?#@!$&'*+,;=%-]*\)"
    r"[A-Za-z0-9._~:/?#@!$&'*+,;=%-]*)*"
)
_EXCESS_BLANK_LINES_PATTERN = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class CleanedMoegirlPage:
    title: str
    source_url: str
    markdown: str
    is_disambiguation: bool


class MoegirlMarkdownCleaner:
    def clean(self, page: MoegirlPage, fetched_at: datetime) -> CleanedMoegirlPage:
        is_disambiguation = (
            "消歧义页" in page.categories
            or self._has_disambiguation_notice(page.article_html)
        )
        soup = BeautifulSoup(page.article_html, "html.parser")
        self._remove_noise(soup)

        converter = html2text.HTML2Text()
        converter.ignore_links = True
        converter.ignore_images = True
        converter.body_width = 0
        converter.unicode_snob = True
        converter.ignore_tables = False
        article_markdown = self._normalize_markdown(converter.handle(str(soup)))
        if not is_disambiguation:
            article_markdown = self._trim_regular_markdown(article_markdown)

        attribution = (
            f"# {page.title}\n\n"
            f"来源：{page.source_url}\n\n"
            f"抓取时间：{fetched_at.isoformat()}"
        )
        markdown = f"{attribution}\n\n{article_markdown}" if article_markdown else attribution
        return CleanedMoegirlPage(
            title=page.title,
            source_url=page.source_url,
            markdown=markdown,
            is_disambiguation=is_disambiguation,
        )

    @staticmethod
    def _has_disambiguation_notice(article_html: str) -> bool:
        text = BeautifulSoup(article_html, "html.parser").get_text(" ", strip=True)
        return "消歧义页" in text or bool(re.search(r"可以指\s*[：:]", text))

    @staticmethod
    def _remove_noise(soup: BeautifulSoup) -> None:
        for selector in _NOISE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

    @staticmethod
    def _trim_regular_markdown(markdown: str) -> str:
        lines = markdown.splitlines()
        start_index = next(
            (index for index, line in enumerate(lines) if "基本资料" in line),
            None,
        )
        if start_index is None:
            introduction = re.compile(r"^#{1,6}\s+简介(?:\s|$)", re.IGNORECASE)
            start_index = next(
                (
                    index
                    for index, line in enumerate(lines)
                    if introduction.search(line.strip())
                ),
                None,
            )
        if start_index is not None:
            lines = lines[start_index:]

        filtered_lines: list[str] = []
        skipped_level: int | None = None
        heading_pattern = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
        for line in lines:
            if re.sub(r"\W", "", line) == "查论编":
                break

            heading = heading_pattern.match(line.strip())
            if heading is not None:
                level = len(heading.group(1))
                title = re.sub(r"\W", "", heading.group(2))
                if skipped_level is not None and level <= skipped_level:
                    skipped_level = None
                if (level == 3 and title.startswith("技能")) or (
                    level == 2 and title.startswith("角色相关")
                ):
                    skipped_level = level
                    continue

            if skipped_level is None:
                filtered_lines.append(line)

        return _EXCESS_BLANK_LINES_PATTERN.sub(
            "\n\n", "\n".join(filtered_lines)
        ).strip()

    @staticmethod
    def _normalize_markdown(markdown: str) -> str:
        without_urls = _RAW_URL_PATTERN.sub("", markdown)
        lines = [re.sub(r"[ \t]+", " ", line).rstrip() for line in without_urls.splitlines()]
        return _EXCESS_BLANK_LINES_PATTERN.sub("\n\n", "\n".join(lines)).strip()
