from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from AgentBI.src.services.toolbox.moegirl.cleaner import CleanedMoegirlPage


_ARTIFACT_ID_PATTERN = re.compile(r"^[a-f0-9]{24}$")


@dataclass(frozen=True)
class MoegirlArtifactSummary:
    id: str
    requested_name: str
    title: str
    source_url: str
    fetched_at: str
    updated_at: str
    character_count: int
    content_sha256: str


@dataclass(frozen=True)
class MoegirlArtifactDocument(MoegirlArtifactSummary):
    markdown: str


class MoegirlArtifactStore:
    def __init__(self, root: Path | None = None) -> None:
        default_root = (
            Path(__file__).parents[4] / "data" / "toolbox" / "moegirl"
        )
        self.root = (root if root is not None else default_root).resolve()

    def list(self, user_id: str) -> list[MoegirlArtifactSummary]:
        user_root = self._user_root(user_id)
        if not user_root.is_dir():
            return []

        summaries: list[MoegirlArtifactSummary] = []
        for child in user_root.iterdir():
            if _ARTIFACT_ID_PATTERN.fullmatch(child.name) is None:
                continue
            if self._is_link_or_reparse_point(child):
                continue
            try:
                resolved_child = child.resolve()
            except OSError:
                continue
            if not resolved_child.is_relative_to(user_root) or not resolved_child.is_dir():
                continue
            summary = self._read_summary(resolved_child, child.name)
            if summary is None:
                continue
            summaries.append(summary)
        return sorted(
            summaries,
            key=lambda item: (-self._timestamp(item.updated_at), item.id),
        )

    def get(
        self,
        user_id: str,
        artifact_id: str,
    ) -> MoegirlArtifactDocument | None:
        artifact_dir = self._artifact_dir(user_id, artifact_id)
        if artifact_dir is None:
            return None

        summary = self._read_summary(artifact_dir, artifact_id)
        if summary is None:
            return None
        content_path = artifact_dir / "content.md"
        try:
            markdown = content_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return None

        return MoegirlArtifactDocument(
            id=summary.id,
            requested_name=summary.requested_name,
            title=summary.title,
            source_url=summary.source_url,
            fetched_at=summary.fetched_at,
            updated_at=summary.updated_at,
            character_count=summary.character_count,
            content_sha256=summary.content_sha256,
            markdown=markdown,
        )

    def save(
        self,
        user_id: str,
        requested_name: str,
        cleaned: CleanedMoegirlPage,
        fetched_at: datetime | None = None,
    ) -> MoegirlArtifactSummary:
        artifact_id = self._digest_prefix(cleaned.title.strip())
        artifact_dir = self._artifact_dir(user_id, artifact_id)
        if artifact_dir is None:
            raise ValueError("invalid artifact path")
        artifact_dir.mkdir(parents=True, exist_ok=True)

        timestamp = fetched_at if fetched_at is not None else datetime.now(timezone.utc)
        timestamp_text = timestamp.isoformat()
        existing = self._read_summary(artifact_dir, artifact_id)
        summary = MoegirlArtifactSummary(
            id=artifact_id,
            requested_name=requested_name,
            title=cleaned.title,
            source_url=cleaned.source_url,
            fetched_at=(
                existing.fetched_at if existing is not None else timestamp_text
            ),
            updated_at=timestamp_text,
            character_count=len(cleaned.markdown),
            content_sha256=hashlib.sha256(
                cleaned.markdown.encode("utf-8")
            ).hexdigest(),
        )
        metadata = {
            "id": summary.id,
            "requested_name": summary.requested_name,
            "title": summary.title,
            "source_url": summary.source_url,
            "fetched_at": summary.fetched_at,
            "updated_at": summary.updated_at,
            "character_count": summary.character_count,
            "content_sha256": summary.content_sha256,
        }

        content_target = artifact_dir / "content.md"
        metadata_target = artifact_dir / "metadata.json"
        content_temp = artifact_dir / "content.md.tmp"
        metadata_temp = artifact_dir / "metadata.json.tmp"
        content_backup = artifact_dir / "content.md.bak"
        metadata_backup = artifact_dir / "metadata.json.bak"
        pairs = (
            (content_temp, content_target, content_backup),
            (metadata_temp, metadata_target, metadata_backup),
        )

        try:
            content_temp.write_text(cleaned.markdown, encoding="utf-8")
            metadata_temp.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            self._replace_pair_atomically(pairs)
        finally:
            content_temp.unlink(missing_ok=True)
            metadata_temp.unlink(missing_ok=True)

        return summary

    def replace_markdown(
        self,
        user_id: str,
        artifact_id: str,
        markdown: str,
        updated_at: datetime | None = None,
    ) -> MoegirlArtifactDocument | None:
        existing = self.get(user_id, artifact_id)
        if existing is None:
            return None

        cleaned = CleanedMoegirlPage(
            title=existing.title,
            source_url=existing.source_url,
            markdown=markdown,
            is_disambiguation=False,
        )
        summary = self.save(
            user_id,
            existing.requested_name,
            cleaned,
            updated_at,
        )
        return MoegirlArtifactDocument(
            **summary.__dict__,
            markdown=markdown,
        )

    def delete(self, user_id: str, artifact_id: str) -> bool:
        artifact_dir = self._artifact_dir(user_id, artifact_id)
        if artifact_dir is None or not artifact_dir.is_dir():
            return False
        shutil.rmtree(artifact_dir)
        return True

    def _user_root(self, user_id: str) -> Path:
        user_root = (
            self.root / "users" / self._digest_prefix(user_id)
        ).resolve()
        if not user_root.is_relative_to(self.root):
            raise ValueError("invalid user path")
        return user_root

    def _artifact_dir(self, user_id: str, artifact_id: str) -> Path | None:
        if _ARTIFACT_ID_PATTERN.fullmatch(artifact_id) is None:
            return None
        user_root = self._user_root(user_id)
        artifact_dir = (user_root / artifact_id).resolve()
        if not artifact_dir.is_relative_to(user_root):
            return None
        return artifact_dir

    @staticmethod
    def _read_summary(
        artifact_dir: Path,
        artifact_id: str,
    ) -> MoegirlArtifactSummary | None:
        try:
            metadata = json.loads(
                (artifact_dir / "metadata.json").read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError):
            return None
        if not isinstance(metadata, dict) or metadata.get("id") != artifact_id:
            return None

        string_fields = (
            "requested_name",
            "title",
            "source_url",
            "fetched_at",
            "updated_at",
            "content_sha256",
        )
        if not all(isinstance(metadata.get(key), str) for key in string_fields):
            return None
        try:
            datetime.fromisoformat(metadata["fetched_at"])
            datetime.fromisoformat(metadata["updated_at"])
        except ValueError:
            return None
        character_count = metadata.get("character_count")
        if not isinstance(character_count, int) or isinstance(character_count, bool):
            return None
        if re.fullmatch(r"[a-f0-9]{64}", metadata["content_sha256"]) is None:
            return None

        return MoegirlArtifactSummary(
            id=artifact_id,
            requested_name=metadata["requested_name"],
            title=metadata["title"],
            source_url=metadata["source_url"],
            fetched_at=metadata["fetched_at"],
            updated_at=metadata["updated_at"],
            character_count=character_count,
            content_sha256=metadata["content_sha256"],
        )

    @staticmethod
    def _digest_prefix(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _is_link_or_reparse_point(path: Path) -> bool:
        try:
            if path.is_symlink():
                return True
            is_junction = getattr(path, "is_junction", None)
            if callable(is_junction) and is_junction():
                return True
            attributes = getattr(path.lstat(), "st_file_attributes", 0)
        except OSError:
            return True
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        return bool(attributes & reparse_flag)

    @staticmethod
    def _timestamp(value: str) -> float:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()

    @staticmethod
    def _replace_pair_atomically(
        pairs: tuple[tuple[Path, Path, Path], ...],
    ) -> None:
        moved_to_backup: list[tuple[Path, Path]] = []
        committed_targets: list[Path] = []
        try:
            for _, target, backup in pairs:
                backup.unlink(missing_ok=True)
                if target.exists():
                    target.replace(backup)
                    moved_to_backup.append((target, backup))
            for temporary, target, _ in pairs:
                temporary.replace(target)
                committed_targets.append(target)
        except BaseException:
            for target in reversed(committed_targets):
                target.unlink(missing_ok=True)
            for target, backup in reversed(moved_to_backup):
                if backup.exists():
                    backup.replace(target)
            raise
        else:
            for _, _, backup in pairs:
                backup.unlink(missing_ok=True)
