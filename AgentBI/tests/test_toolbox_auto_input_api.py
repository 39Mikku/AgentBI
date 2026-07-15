import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.schemas.toolbox_auto_input_schema import AutoInputJobResponse
from AgentBI.src.services.toolbox.auto_input.service import AutoInputBusyError


def job(status="countdown"):
    return AutoInputJobResponse(
        id="typing-1",
        status=status,
        delay_seconds=0.05,
        countdown_seconds=5,
        countdown_remaining=4 if status == "countdown" else 0,
        total_characters=5,
        typed_characters=0,
        created_at="2026-07-15T10:00:00",
    )


class FakeAutoInputService:
    def __init__(self):
        self.active = job()

    def start(self, payload):
        if payload.text == "busy":
            raise AutoInputBusyError("已有自动输入任务正在运行")
        self.active = job()
        return self.active

    def get_active(self):
        return self.active

    def get(self, job_id):
        return self.active if job_id == "typing-1" else None

    def cancel(self, job_id):
        if job_id != "typing-1":
            return None
        self.active = job("cancelled")
        return self.active


class ToolboxAutoInputApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.toolbox_auto_input import router

        app = FastAPI()
        app.state.auto_input_service = FakeAutoInputService()
        app.include_router(router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_start_active_status_and_cancel_contract(self):
        created = self.client.post(
            "/toolbox/auto-input/jobs",
            json={"text": "hello", "delay_seconds": 0.05, "countdown_seconds": 5},
        )
        self.assertEqual(created.status_code, 202)
        self.assertEqual(created.json()["id"], "typing-1")

        active = self.client.get("/toolbox/auto-input/jobs/active")
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.json()["countdown_remaining"], 4)

        status = self.client.get("/toolbox/auto-input/jobs/typing-1")
        self.assertEqual(status.status_code, 200)
        cancelled = self.client.post("/toolbox/auto-input/jobs/typing-1/cancel")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["status"], "cancelled")

    def test_missing_and_busy_jobs_map_to_clear_statuses(self):
        missing = self.client.get("/toolbox/auto-input/jobs/missing")
        self.assertEqual(missing.status_code, 404)
        busy = self.client.post(
            "/toolbox/auto-input/jobs",
            json={"text": "busy", "delay_seconds": 0.05, "countdown_seconds": 5},
        )
        self.assertEqual(busy.status_code, 409)

    def test_active_endpoint_returns_no_content_when_idle(self):
        self.client.app.state.auto_input_service.active = None
        response = self.client.get("/toolbox/auto-input/jobs/active")
        self.assertEqual(response.status_code, 204)


if __name__ == "__main__":
    unittest.main()
