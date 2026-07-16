from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from AgentBI.src.services.toolbox.moegirl.artifact_store import (
    MoegirlArtifactStore,
    MoegirlArtifactSummary,
)
from AgentBI.src.services.toolbox.moegirl.cleaner import MoegirlMarkdownCleaner
from AgentBI.src.services.toolbox.moegirl.scraper import MoegirlScraper


@dataclass(frozen=True)
class MoegirlFetchResult:
    kind: str
    title: str
    source_url: str
    markdown: str
    message: str
    artifact: MoegirlArtifactSummary | None


class MoegirlArchiveService:
    def __init__(
        self,
        scraper: MoegirlScraper | None = None,
        cleaner: MoegirlMarkdownCleaner | None = None,
        store: MoegirlArtifactStore | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.scraper = scraper if scraper is not None else MoegirlScraper()
        self.cleaner = cleaner if cleaner is not None else MoegirlMarkdownCleaner()
        self.store = store if store is not None else MoegirlArtifactStore()
        self.clock = (
            clock
            if clock is not None
            else lambda: datetime.now(timezone.utc)
        )

    async def fetch(self, user_id: str, name: str) -> MoegirlFetchResult:
        page = await self.scraper.fetch(name)
        fetched_at = self.clock()
        cleaned = self.cleaner.clean(page, fetched_at)
        if cleaned.is_disambiguation:
            return MoegirlFetchResult(
                kind="disambiguation",
                title=cleaned.title,
                source_url=cleaned.source_url,
                markdown=cleaned.markdown,
                message="该名称指向消歧义页，预览不会保存",
                artifact=None,
            )

        artifact = self.store.save(user_id, name, cleaned, fetched_at)
        return MoegirlFetchResult(
            kind="saved",
            title=cleaned.title,
            source_url=cleaned.source_url,
            markdown=cleaned.markdown,
            message="抓取完成并已保存",
            artifact=artifact,
        )
