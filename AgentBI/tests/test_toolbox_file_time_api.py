import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.schemas.toolbox_file_time_schema import FileTimeJobResponse, FileTimePreview


class FakeDirectoryPicker:
    def choose(self, title: str, initial_directory: str | None = None):
        if title == "取消":
            return None
        return r"C:\Media"


class FakeFileTimeService:
    def __init__(self):
        self.payload = None

    def preview(self, payload):
        self.payload = payload
        return FileTimePreview(
            operation=payload.operation,
            total_files=3,
            update_count=3,
            examples=["a.jpg"],
        )

    def start(self, payload):
        self.payload = payload
        return FileTimeJobResponse(
            id="job-1",
            operation=payload.operation,
            status="queued",
        )

    def get_job(self, job_id):
        if job_id != "job-1":
            return None
        return FileTimeJobResponse(
            id="job-1",
            operation="creation_from_modified",
            status="completed",
            total_files=3,
            processed_files=3,
            updated_count=3,
        )


class ToolboxFileTimeApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.toolbox_file_time import router as file_time_router
        from AgentBI.src.api.toolbox_system import router as system_router

        app = FastAPI()
        app.state.directory_picker = FakeDirectoryPicker()
        app.state.file_time_service = FakeFileTimeService()
        app.include_router(system_router)
        app.include_router(file_time_router)
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def test_select_directory_returns_path_and_cancellation(self):
        selected = self.client.post(
            "/toolbox/system/select-directory",
            json={"title": "选择输入目录"},
        )
        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json(), {"path": r"C:\Media", "cancelled": False})

        cancelled = self.client.post(
            "/toolbox/system/select-directory",
            json={"title": "取消"},
        )
        self.assertEqual(cancelled.json(), {"path": None, "cancelled": True})

    def test_preview_start_and_status_contract(self):
        payload = {
            "operation": "creation_from_modified",
            "input_directory": r"C:\Media",
        }
        preview = self.client.post("/toolbox/file-time/preview", json=payload)
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(preview.json()["total_files"], 3)

        created = self.client.post("/toolbox/file-time/jobs", json=payload)
        self.assertEqual(created.status_code, 202)
        self.assertEqual(created.json()["id"], "job-1")

        status = self.client.get("/toolbox/file-time/jobs/job-1")
        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["updated_count"], 3)
        self.assertEqual(self.client.get("/toolbox/file-time/jobs/missing").status_code, 404)

    def test_invalid_payload_is_unprocessable(self):
        response = self.client.post(
            "/toolbox/file-time/preview",
            json={
                "operation": "filename_to_creation",
                "input_directory": r"C:\Media",
            },
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
