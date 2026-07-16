import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from AgentBI.src.services.toolbox.moegirl.artifact_store import MoegirlArtifactStore
from AgentBI.src.services.toolbox.moegirl.cleaner import CleanedMoegirlPage


FIRST_TIME = datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc)
SECOND_TIME = datetime(2026, 7, 15, 13, 0, 0, tzinfo=timezone.utc)
THIRD_TIME = datetime(2026, 7, 15, 14, 0, 0, tzinfo=timezone.utc)


def cleaned_page(title: str, markdown: str) -> CleanedMoegirlPage:
    return CleanedMoegirlPage(
        title=title,
        source_url=f"https://mzh.moegirl.org.cn/{title}",
        markdown=markdown,
        is_disambiguation=False,
    )


class MoegirlArtifactStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.store = MoegirlArtifactStore(self.root)

    def test_default_root_is_agentbi_data_directory(self):
        expected = (
            Path(__file__).resolve().parents[1]
            / "data"
            / "toolbox"
            / "moegirl"
        )

        self.assertEqual(MoegirlArtifactStore().root, expected)

    def test_save_uses_users_hashed_directory_layout(self):
        artifact = self.store.save(
            "alice", "可莉", cleaned_page("可莉", "content")
        )
        user_hash = hashlib.sha256(b"alice").hexdigest()[:24]
        artifact_dir = self.root / "users" / user_hash / artifact.id

        self.assertTrue((artifact_dir / "metadata.json").is_file())
        self.assertTrue((artifact_dir / "content.md").is_file())

    def test_save_upserts_one_artifact_per_user_and_canonical_title(self):
        first = self.store.save(
            "alice", "芽衣", cleaned_page("雷电芽衣", "first")
        )
        second = self.store.save(
            "alice", "雷电芽衣", cleaned_page("雷电芽衣", "second")
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(len(self.store.list("alice")), 1)
        document = self.store.get("alice", first.id)
        self.assertIsNotNone(document)
        self.assertEqual(document.markdown, "second")

    def test_refresh_preserves_fetched_at_and_updates_content_metadata(self):
        first_markdown = "first 雷电芽衣"
        second_markdown = "second 雷电芽衣 with more text"
        first = self.store.save(
            "alice",
            "芽衣",
            cleaned_page("雷电芽衣", first_markdown),
            FIRST_TIME,
        )
        second = self.store.save(
            "alice",
            "雷电芽衣",
            cleaned_page("雷电芽衣", second_markdown),
            SECOND_TIME,
        )

        expected_hash = hashlib.sha256(second_markdown.encode("utf-8")).hexdigest()
        self.assertEqual(first.fetched_at, FIRST_TIME.isoformat())
        self.assertEqual(first.updated_at, FIRST_TIME.isoformat())
        self.assertEqual(second.fetched_at, FIRST_TIME.isoformat())
        self.assertEqual(second.updated_at, SECOND_TIME.isoformat())
        self.assertEqual(second.character_count, len(second_markdown))
        self.assertEqual(second.content_sha256, expected_hash)

        user_hash = hashlib.sha256(b"alice").hexdigest()[:24]
        metadata_path = (
            self.root / "users" / user_hash / second.id / "metadata.json"
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        self.assertEqual(
            set(metadata),
            {
                "id",
                "title",
                "requested_name",
                "source_url",
                "fetched_at",
                "updated_at",
                "character_count",
                "content_sha256",
            },
        )
        self.assertEqual(metadata["fetched_at"], FIRST_TIME.isoformat())
        self.assertEqual(metadata["updated_at"], SECOND_TIME.isoformat())
        self.assertEqual(metadata["character_count"], len(second_markdown))
        self.assertEqual(metadata["content_sha256"], expected_hash)

        document = self.store.get("alice", second.id)
        self.assertIsNotNone(document)
        self.assertEqual(document.fetched_at, FIRST_TIME.isoformat())
        self.assertEqual(document.updated_at, SECOND_TIME.isoformat())
        self.assertEqual(document.character_count, len(second_markdown))
        self.assertEqual(document.content_sha256, expected_hash)
        self.assertEqual(document.markdown, second_markdown)

    def test_users_are_isolated(self):
        artifact = self.store.save(
            "alice", "可莉", cleaned_page("可莉", "content")
        )

        self.assertIsNone(self.store.get("bob", artifact.id))
        self.assertEqual(self.store.list("bob"), [])
        self.assertFalse(self.store.delete("bob", artifact.id))
        self.assertIsNotNone(self.store.get("alice", artifact.id))

    def test_list_orders_newest_artifact_first(self):
        self.store.save(
            "alice", "Alpha", cleaned_page("Alpha", "first"), FIRST_TIME
        )
        self.store.save(
            "alice", "Zulu", cleaned_page("Zulu", "second"), SECOND_TIME
        )

        self.assertEqual(
            [artifact.title for artifact in self.store.list("alice")],
            ["Zulu", "Alpha"],
        )

    def test_list_reads_metadata_without_requiring_content(self):
        artifact = self.store.save(
            "alice", "可莉", cleaned_page("可莉", "content"), FIRST_TIME
        )
        user_hash = hashlib.sha256(b"alice").hexdigest()[:24]
        content_path = (
            self.root / "users" / user_hash / artifact.id / "content.md"
        )
        content_path.unlink()

        summaries = self.store.list("alice")

        self.assertEqual([summary.id for summary in summaries], [artifact.id])
        self.assertEqual(summaries[0].character_count, len("content"))
        self.assertIsNone(self.store.get("alice", artifact.id))

    def test_list_rejects_entries_marked_as_symbolic_links(self):
        artifact = self.store.save(
            "alice", "可莉", cleaned_page("可莉", "content"), FIRST_TIME
        )
        user_hash = hashlib.sha256(b"alice").hexdigest()[:24]
        artifact_dir = self.root / "users" / user_hash / artifact.id
        original_is_symlink = Path.is_symlink

        def report_artifact_as_symlink(path: Path) -> bool:
            if path == artifact_dir:
                return True
            return original_is_symlink(path)

        with patch.object(Path, "is_symlink", new=report_artifact_as_symlink):
            self.assertEqual(self.store.list("alice"), [])

    def test_list_rejects_resolved_children_outside_user_root(self):
        artifact = self.store.save(
            "alice", "可莉", cleaned_page("可莉", "content"), FIRST_TIME
        )
        user_hash = hashlib.sha256(b"alice").hexdigest()[:24]
        user_root = self.root / "users" / user_hash
        artifact_dir = user_root / artifact.id
        outside_dir = self.root / "outside" / artifact.id
        outside_dir.mkdir(parents=True)
        (outside_dir / "metadata.json").write_text(
            (artifact_dir / "metadata.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        original_resolve = Path.resolve

        def resolve_outside(path: Path, *args, **kwargs) -> Path:
            if path == artifact_dir:
                return outside_dir
            return original_resolve(path, *args, **kwargs)

        with patch.object(Path, "resolve", new=resolve_outside):
            self.assertEqual(self.store.list("alice"), [])

    def test_refresh_moves_existing_artifact_to_front(self):
        self.store.save(
            "alice", "Zulu", cleaned_page("Zulu", "first"), FIRST_TIME
        )
        self.store.save(
            "alice", "Alpha", cleaned_page("Alpha", "second"), SECOND_TIME
        )
        self.store.save(
            "alice", "Zulu", cleaned_page("Zulu", "refreshed"), THIRD_TIME
        )

        artifacts = self.store.list("alice")
        self.assertEqual([artifact.title for artifact in artifacts], ["Zulu", "Alpha"])
        self.assertEqual(artifacts[0].updated_at, THIRD_TIME.isoformat())

    def test_delete_removes_only_the_selected_artifact(self):
        selected = self.store.save(
            "alice", "可莉", cleaned_page("可莉", "first")
        )
        retained = self.store.save(
            "alice", "琴", cleaned_page("琴", "second")
        )

        self.assertTrue(self.store.delete("alice", selected.id))

        self.assertIsNone(self.store.get("alice", selected.id))
        self.assertIsNotNone(self.store.get("alice", retained.id))
        self.assertEqual([item.id for item in self.store.list("alice")], [retained.id])

    def test_invalid_artifact_ids_are_rejected_without_path_traversal(self):
        outside = self.root / "outside"
        outside.mkdir()
        marker = outside / "marker.txt"
        marker.write_text("keep", encoding="utf-8")

        for artifact_id in ("../outside", "A" * 24, "a" * 23, "g" * 24):
            with self.subTest(artifact_id=artifact_id):
                self.assertIsNone(self.store.get("alice", artifact_id))
                self.assertFalse(self.store.delete("alice", artifact_id))

        self.assertEqual(marker.read_text(encoding="utf-8"), "keep")

    def test_refresh_write_failure_preserves_existing_artifact(self):
        artifact = self.store.save(
            "alice", "可莉", cleaned_page("可莉", "original")
        )
        original_write_text = Path.write_text

        def fail_metadata_write(path: Path, data: str, *args, **kwargs):
            if path.name == "metadata.json.tmp":
                raise OSError("metadata write failed")
            return original_write_text(path, data, *args, **kwargs)

        with patch.object(Path, "write_text", new=fail_metadata_write):
            with self.assertRaisesRegex(OSError, "metadata write failed"):
                self.store.save(
                    "alice", "可莉", cleaned_page("可莉", "replacement")
                )

        document = self.store.get("alice", artifact.id)
        self.assertIsNotNone(document)
        self.assertEqual(document.markdown, "original")
        self.assertEqual(len(self.store.list("alice")), 1)
        self.assertEqual(list(self.root.rglob("*.tmp")), [])

    def test_refresh_replace_failure_rolls_back_both_files(self):
        artifact = self.store.save(
            "alice", "可莉", cleaned_page("可莉", "original")
        )
        original_replace = Path.replace

        def fail_metadata_replace(path: Path, target: Path):
            if path.name == "metadata.json.tmp":
                raise OSError("metadata replace failed")
            return original_replace(path, target)

        with patch.object(Path, "replace", new=fail_metadata_replace):
            with self.assertRaisesRegex(OSError, "metadata replace failed"):
                self.store.save(
                    "alice", "changed request", cleaned_page("可莉", "replacement")
                )

        document = self.store.get("alice", artifact.id)
        self.assertIsNotNone(document)
        self.assertEqual(document.requested_name, "可莉")
        self.assertEqual(document.markdown, "original")
        self.assertEqual(list(self.root.rglob("*.tmp")), [])
        self.assertEqual(list(self.root.rglob("*.bak")), [])


if __name__ == "__main__":
    unittest.main()
