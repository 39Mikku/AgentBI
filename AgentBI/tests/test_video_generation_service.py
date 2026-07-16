import tempfile
import unittest
from pathlib import Path

import httpx

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository


class AgnesClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_request_contains_only_fixed_text_to_video_fields(self):
        from AgentBI.src.services.video_generation.agnes_client import AgnesVideoClient

        captured = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured.update(__import__("json").loads(request.content))
            return httpx.Response(
                200,
                json={"video_id": "video-1", "status": "queued", "progress": 0},
            )

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test")
        client = AgnesVideoClient("secret", base_url="https://example.test", http_client=http)
        try:
            result = await client.create_video(
                prompt="A quiet lake at dawn",
                width=1280,
                height=720,
                num_frames=121,
            )
        finally:
            await http.aclose()

        self.assertEqual(result["video_id"], "video-1")
        self.assertEqual(
            captured,
            {
                "model": "agnes-video-v2.0",
                "prompt": "A quiet lake at dawn",
                "width": 1280,
                "height": 720,
                "num_frames": 121,
                "frame_rate": 24,
            },
        )


class VideoJobRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = SqliteChatRepository(":memory:")

    def tearDown(self):
        self.repository.close()

    def test_job_round_trip_and_active_recovery_query(self):
        job = self.repository.create_video_generation_job(
            {
                "user_id": "user@example.com",
                "conversation_id": "conversation-1",
                "message_id": None,
                "prompt": "A quiet lake at dawn",
                "aspect_ratio": "16:9",
                "duration_seconds": 5,
                "num_frames": 121,
                "frame_rate": 24,
            }
        )
        updated = self.repository.update_video_generation_job(
            job["_id"],
            {"provider_video_id": "video-1", "status": "in_progress", "progress": 38},
        )

        self.assertEqual(updated["progress"], 38)
        self.assertEqual(updated["provider_video_id"], "video-1")
        self.assertEqual(
            [item["_id"] for item in self.repository.list_active_video_generation_jobs()],
            [job["_id"]],
        )
        self.assertIsNone(self.repository.get_video_generation_job(job["_id"], "other@example.com"))


class FakeAgnesClient:
    def __init__(self):
        self.created = []
        self.poll_count = 0

    async def create_video(self, **payload):
        self.created.append(payload)
        return {"video_id": "video-1", "status": "queued", "progress": 0}

    async def get_video(self, video_id):
        self.poll_count += 1
        if self.poll_count == 1:
            return {"video_id": video_id, "status": "in_progress", "progress": 47}
        return {
            "video_id": video_id,
            "status": "completed",
            "progress": 100,
            "url": "https://cdn.example.test/video.mp4",
        }

    async def download_video(self, url):
        return b"\x00\x00\x00\x18ftypmp42video-bytes"


class FakeAssetService:
    def __init__(self):
        self.registered = []

    def register_generated_video(self, **payload):
        self.registered.append(payload)
        return {"_id": "asset-1"}


class VideoGenerationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.repository = SqliteChatRepository(":memory:")

    async def asyncTearDown(self):
        self.repository.close()
        self.directory.cleanup()

    async def test_submit_returns_queued_then_worker_downloads_and_completes(self):
        from AgentBI.src.services.video_generation.service import VideoGenerationService

        client = FakeAgnesClient()
        assets = FakeAssetService()
        service = VideoGenerationService(
            repository=self.repository,
            client=client,
            output_root=Path(self.directory.name),
            asset_service=assets,
            poll_interval=0,
        )

        queued = await service.submit(
            user_id="user@example.com",
            conversation_id="conversation-1",
            message_id=None,
            prompt="A quiet lake at dawn",
            aspect_ratio="16:9",
            duration_seconds=5,
        )
        self.assertEqual(queued["status"], "queued")
        self.assertEqual(queued["provider_video_id"], "video-1")

        await service.wait_for_job(queued["_id"])
        completed = service.get_job(queued["_id"], "user@example.com")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["progress"], 100)
        self.assertEqual(completed["asset_id"], "asset-1")
        self.assertEqual(client.created[0]["num_frames"], 121)
        self.assertTrue((Path(self.directory.name) / assets.registered[0]["relative_path"]).is_file())
        await service.shutdown()

    async def test_start_resumes_an_active_sqlite_job_after_restart(self):
        from AgentBI.src.services.video_generation.service import VideoGenerationService

        job = self.repository.create_video_generation_job(
            {
                "user_id": "user@example.com",
                "conversation_id": "conversation-1",
                "message_id": None,
                "prompt": "A quiet lake at dawn",
                "aspect_ratio": "16:9",
                "duration_seconds": 3,
                "num_frames": 81,
                "frame_rate": 24,
            }
        )
        self.repository.update_video_generation_job(
            job["_id"],
            {"provider_video_id": "video-before-restart", "status": "in_progress", "progress": 26},
        )
        client = FakeAgnesClient()
        assets = FakeAssetService()
        service = VideoGenerationService(
            repository=self.repository,
            client=client,
            output_root=Path(self.directory.name),
            asset_service=assets,
            poll_interval=0,
        )

        await service.start()
        await service.wait_for_job(job["_id"])

        completed = service.get_job(job["_id"], "user@example.com")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["asset_id"], "asset-1")
        self.assertGreaterEqual(client.poll_count, 1)
        await service.shutdown()


if __name__ == "__main__":
    unittest.main()
