import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from AgentBI.src.services.toolbox.moegirl.artifact_store import (
    MoegirlArtifactStore,
    MoegirlArtifactSummary,
)
from AgentBI.src.services.toolbox.moegirl.cleaner import (
    CleanedMoegirlPage,
    MoegirlMarkdownCleaner,
)
from AgentBI.src.services.toolbox.moegirl.scraper import MoegirlPage, MoegirlScraper
from AgentBI.src.services.toolbox.moegirl.service import MoegirlArchiveService


FIXED_TIME = datetime(2026, 7, 15, 12, 34, 56, tzinfo=timezone.utc)


def page(title: str) -> MoegirlPage:
    return MoegirlPage(
        title=title,
        source_url=f"https://mzh.moegirl.org.cn/{title}",
        article_html="<p>正文</p>",
        categories=(),
    )


def cleaned_page(title: str, *, disambiguation: bool) -> CleanedMoegirlPage:
    return CleanedMoegirlPage(
        title=title,
        source_url=f"https://mzh.moegirl.org.cn/{title}",
        markdown=f"# {title}\n\n正文",
        is_disambiguation=disambiguation,
    )


class MoegirlArchiveServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.scraper = AsyncMock(spec=MoegirlScraper)
        self.cleaner = Mock(spec=MoegirlMarkdownCleaner)
        self.store = Mock(spec=MoegirlArtifactStore)
        self.clock = Mock(return_value=FIXED_TIME)
        self.service = MoegirlArchiveService(
            scraper=self.scraper,
            cleaner=self.cleaner,
            store=self.store,
            clock=self.clock,
        )

    async def test_regular_page_is_saved(self):
        scraped = page("雷电芽衣")
        cleaned = cleaned_page("雷电芽衣", disambiguation=False)
        artifact = MoegirlArtifactSummary(
            id="a" * 24,
            requested_name="雷电芽衣",
            title=cleaned.title,
            source_url=cleaned.source_url,
            fetched_at=FIXED_TIME.isoformat(),
            updated_at=FIXED_TIME.isoformat(),
            character_count=len(cleaned.markdown),
            content_sha256="a" * 64,
        )
        self.scraper.fetch.return_value = scraped
        self.cleaner.clean.return_value = cleaned
        self.store.save.return_value = artifact

        result = await self.service.fetch("alice", "雷电芽衣")

        self.assertEqual(result.kind, "saved")
        self.assertEqual(result.title, cleaned.title)
        self.assertEqual(result.source_url, cleaned.source_url)
        self.assertEqual(result.markdown, cleaned.markdown)
        self.assertEqual(result.message, "抓取完成并已保存")
        self.assertIs(result.artifact, artifact)
        self.scraper.fetch.assert_awaited_once_with("雷电芽衣")
        self.cleaner.clean.assert_called_once_with(scraped, FIXED_TIME)
        self.store.save.assert_called_once_with(
            "alice", "雷电芽衣", cleaned, FIXED_TIME
        )
        self.clock.assert_called_once_with()

    async def test_disambiguation_is_previewed_without_persistence(self):
        scraped = page("芽衣")
        cleaned = cleaned_page("芽衣", disambiguation=True)
        self.scraper.fetch.return_value = scraped
        self.cleaner.clean.return_value = cleaned

        result = await self.service.fetch("alice", "芽衣")

        self.assertEqual(result.kind, "disambiguation")
        self.assertEqual(result.title, cleaned.title)
        self.assertEqual(result.source_url, cleaned.source_url)
        self.assertEqual(result.markdown, cleaned.markdown)
        self.assertEqual(result.message, "该名称指向消歧义页，预览不会保存")
        self.assertIsNone(result.artifact)
        self.scraper.fetch.assert_awaited_once_with("芽衣")
        self.cleaner.clean.assert_called_once_with(scraped, FIXED_TIME)
        self.store.save.assert_not_called()
        self.clock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
