import threading
import unittest


class FakeSender:
    def __init__(self):
        self.characters: list[str] = []
        self.after_send = None

    def send_character(self, character: str) -> None:
        self.characters.append(character)
        if self.after_send:
            self.after_send()


class BlockingRunner:
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def run(self, job, cancel_event):
        job.status = "running"
        self.started.set()
        self.release.wait(timeout=2)
        job.status = "cancelled" if cancel_event.is_set() else "completed"


class ToolboxAutoInputServiceTests(unittest.TestCase):
    def payload(self, **changes):
        from AgentBI.src.schemas.toolbox_auto_input_schema import AutoInputCreate

        values = {"text": "hello", "delay_seconds": 0, "countdown_seconds": 1}
        values.update(changes)
        return AutoInputCreate(**values)

    def test_runner_normalizes_newlines_and_reports_progress(self):
        from AgentBI.src.services.toolbox.auto_input.service import AutoInputJob, AutoInputRunner

        sender = FakeSender()
        runner = AutoInputRunner(sender=sender, sleep=lambda _: None)
        job = AutoInputJob(text="你\r\n好", delay_seconds=0, countdown_seconds=1)

        runner.run(job, threading.Event())

        self.assertEqual(sender.characters, ["你", "\n", "好"])
        self.assertEqual(job.typed_characters, 3)
        self.assertEqual(job.total_characters, 3)
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.countdown_remaining, 0)

    def test_runner_stops_on_cancel_after_current_character(self):
        from AgentBI.src.services.toolbox.auto_input.service import AutoInputJob, AutoInputRunner

        sender = FakeSender()
        cancel = threading.Event()
        sender.after_send = cancel.set
        runner = AutoInputRunner(sender=sender, sleep=lambda _: None)
        job = AutoInputJob(text="abc", delay_seconds=0, countdown_seconds=1)

        runner.run(job, cancel)

        self.assertEqual(sender.characters, ["a"])
        self.assertEqual(job.typed_characters, 1)
        self.assertEqual(job.status, "cancelled")

    def test_service_allows_only_one_active_job_and_can_cancel_it(self):
        from AgentBI.src.services.toolbox.auto_input.service import (
            AutoInputBusyError,
            AutoInputService,
        )

        runner = BlockingRunner()
        service = AutoInputService(runner=runner)
        created = service.start(self.payload())
        self.assertTrue(runner.started.wait(timeout=1))

        with self.assertRaises(AutoInputBusyError):
            service.start(self.payload(text="second"))

        cancelled = service.cancel(created.id)
        self.assertIsNotNone(cancelled)
        runner.release.set()
        for _ in range(100):
            job = service.get(created.id)
            if job and job.status == "cancelled":
                break
            threading.Event().wait(0.005)
        self.assertEqual(service.get(created.id).status, "cancelled")

    def test_empty_or_out_of_range_payload_is_rejected(self):
        from pydantic import ValidationError

        for changes in (
            {"text": "   "},
            {"delay_seconds": -0.01},
            {"delay_seconds": 2.01},
            {"countdown_seconds": 0},
            {"countdown_seconds": 31},
        ):
            with self.assertRaises(ValidationError):
                self.payload(**changes)


if __name__ == "__main__":
    unittest.main()
