import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError


class FakeCreationTimeWriter:
    def __init__(self):
        self.calls: list[tuple[Path, float]] = []

    def set_creation_time(self, path: Path, timestamp: float) -> None:
        self.calls.append((path, timestamp))


class ToolboxFileTimeServiceTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.services.toolbox.file_time.service import FileTimeService

        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.input = self.root / "input"
        self.output = self.input / "output"
        self.input.mkdir()
        self.writer = FakeCreationTimeWriter()
        self.service = FileTimeService(creation_time_writer=self.writer)

    def tearDown(self):
        self.temp_dir.cleanup()

    def request(self, **changes):
        from AgentBI.src.schemas.toolbox_file_time_schema import FileTimeRequest

        values = {
            "operation": "creation_from_modified",
            "input_directory": str(self.input),
        }
        values.update(changes)
        return FileTimeRequest(**values)

    def test_extracts_all_supported_filename_formats_and_rejects_invalid_dates(self):
        from AgentBI.src.services.toolbox.file_time.service import extract_filename_time

        expected = datetime(2026, 7, 15, 9, 8, 7)
        for name in (
            "IMG_2026-07-15-09-08-07.jpg",
            "IMG_20260715_090807.jpg",
            "IMG_20260715-090807.jpg",
            "IMG_20260715090807.jpg",
        ):
            self.assertEqual(extract_filename_time(name), expected)
        self.assertIsNone(extract_filename_time("IMG_20260231_090807.jpg"))
        self.assertIsNone(extract_filename_time("plain.jpg"))

    def test_output_and_date_range_validation_follow_operation(self):
        self.request(operation="creation_from_modified")
        self.request(operation="modified_from_creation")
        with self.assertRaises(ValidationError):
            self.request(operation="filename_to_creation")
        with self.assertRaises(ValidationError):
            self.request(operation="move_by_creation_range", output_directory=str(self.output))
        with self.assertRaises(ValidationError):
            self.request(
                operation="move_by_creation_range",
                output_directory=str(self.output),
                start_date="2026-07-16",
                end_date="2026-07-15",
            )

    def test_preview_excludes_nested_output_and_counts_filename_actions(self):
        nested = self.input / "nested"
        nested.mkdir()
        (nested / "IMG_20260715_090807.jpg").write_text("dated", encoding="utf-8")
        (nested / "plain.txt").write_text("plain", encoding="utf-8")
        self.output.mkdir()
        (self.output / "already-moved.txt").write_text("old", encoding="utf-8")

        preview = self.service.preview(
            self.request(
                operation="filename_to_creation",
                output_directory=str(self.output),
            )
        )

        self.assertEqual(preview.total_files, 2)
        self.assertEqual(preview.update_count, 1)
        self.assertEqual(preview.move_count, 1)
        self.assertEqual(preview.skip_count, 0)
        self.assertNotIn("output/already-moved.txt", "/".join(preview.examples))

    def test_filename_mode_updates_matches_and_moves_non_matches(self):
        nested = self.input / "nested"
        nested.mkdir()
        dated = nested / "IMG_20260715_090807.jpg"
        plain = nested / "plain.txt"
        dated.write_text("dated", encoding="utf-8")
        plain.write_text("plain", encoding="utf-8")

        job = self.service.run_now(
            self.request(
                operation="filename_to_creation",
                output_directory=str(self.output),
            )
        )

        self.assertEqual(job.status, "completed")
        self.assertEqual(job.updated_count, 1)
        self.assertEqual(job.moved_count, 1)
        self.assertEqual(job.failed_count, 0)
        self.assertEqual(self.writer.calls[0][0], dated)
        self.assertEqual(
            datetime.fromtimestamp(self.writer.calls[0][1]),
            datetime(2026, 7, 15, 9, 8, 7),
        )
        self.assertTrue((self.output / "nested" / "plain.txt").exists())

    def test_existing_move_target_is_reported_and_never_overwritten(self):
        source = self.input / "same.txt"
        source.write_text("source", encoding="utf-8")
        self.output.mkdir()
        target = self.output / "same.txt"
        target.write_text("existing", encoding="utf-8")

        job = self.service.run_now(
            self.request(
                operation="filename_to_creation",
                output_directory=str(self.output),
            )
        )

        self.assertEqual(job.failed_count, 1)
        self.assertEqual(target.read_text(encoding="utf-8"), "existing")
        self.assertTrue(source.exists())

    def test_creation_from_modified_uses_file_mtime(self):
        path = self.input / "photo.jpg"
        path.write_text("x", encoding="utf-8")
        timestamp = datetime(2024, 1, 2, 3, 4, 5).timestamp()
        os.utime(path, (timestamp, timestamp))

        job = self.service.run_now(self.request(operation="creation_from_modified"))

        self.assertEqual(job.updated_count, 1)
        self.assertAlmostEqual(self.writer.calls[0][1], timestamp, places=3)


if __name__ == "__main__":
    unittest.main()
