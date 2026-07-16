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

    async def test_provider_contract_normalizes_agnes_create_and_query(self):
        from AgentBI.src.services.video_generation.agnes_client import AgnesVideoClient
        from AgentBI.src.services.video_generation.provider import VideoCreateRequest

        responses = iter(
            (
                {"video_id": "video-1", "status": "queued", "progress": 0},
                {
                    "video_id": "video-1",
                    "status": "completed",
                    "progress": 100,
                    "url": "https://cdn.example.test/video.mp4",
                },
            )
        )

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=next(responses))

        http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://example.test"
        )
        client = AgnesVideoClient("secret", base_url="https://example.test", http_client=http)
        try:
            created = await client.create_video(
                VideoCreateRequest(
                    prompt="A quiet lake",
                    model="agnes-video-v2.0",
                    aspect_ratio="16:9",
                    duration_seconds=5,
                    width=1280,
                    height=720,
                    num_frames=121,
                )
            )
            queried = await client.get_video("video-1")
        finally:
            await http.aclose()

        self.assertEqual(created.get("task_id"), "video-1")
        self.assertEqual(queried.get("status"), "completed")
        self.assertEqual(queried.get("url"), "https://cdn.example.test/video.mp4")


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
                "provider": "volcengine",
                "model": "doubao-seedance-1-0-pro-250528",
                "resolution": "720p",
                "generate_audio": False,
                "watermark": False,
                "use_attached_image": True,
            }
        )
        updated = self.repository.update_video_generation_job(
            job["_id"],
            {"provider_video_id": "video-1", "status": "in_progress", "progress": 38},
        )

        self.assertEqual(updated["progress"], 38)
        self.assertEqual(updated["provider_video_id"], "video-1")
        self.assertEqual(updated.get("provider"), "volcengine")
        self.assertEqual(updated.get("model"), "doubao-seedance-1-0-pro-250528")
        self.assertEqual(updated.get("resolution"), "720p")
        self.assertFalse(updated.get("generate_audio"))
        self.assertTrue(updated.get("use_attached_image"))
        self.assertEqual(
            [item["_id"] for item in self.repository.list_active_video_generation_jobs()],
            [job["_id"]],
        )
        self.assertIsNone(self.repository.get_video_generation_job(job["_id"], "other@example.com"))


class FakeAgnesClient:
    provider_id = "agnes"

    def __init__(self):
        self.created = []
        self.poll_count = 0

    async def create_video(self, request):
        self.created.append(request)
        return {"task_id": "video-1", "status": "queued", "progress": 0}

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


class FakeArkProvider:
    provider_id = "volcengine"

    def __init__(self):
        self.created = []
        self.queried = []

    async def create_video(self, request):
        self.created.append(request)
        return {"task_id": "cgt-1", "status": "queued", "progress": 0}

    async def get_video(self, task_id):
        self.queried.append(task_id)
        return {
            "task_id": task_id,
            "status": "completed",
            "progress": 100,
            "url": "https://cdn.example.test/seedance.mp4",
            "metadata": {"resolution": "720p", "generate_audio": False},
        }

    async def download_video(self, url):
        return b"\x00\x00\x00\x18ftypmp42seedance-video"

    async def close(self):
        return None


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
        self.assertEqual(client.created[0].num_frames, 121)
        self.assertTrue((Path(self.directory.name) / assets.registered[0]["relative_path"]).is_file())
        await service.shutdown()

    async def test_submit_maps_requested_duration_to_selected_provider_preset(self):
        from AgentBI.src.services.video_generation.service import VideoGenerationService

        client = FakeAgnesClient()
        service = VideoGenerationService(
            repository=self.repository,
            client=client,
            output_root=Path(self.directory.name),
            asset_service=FakeAssetService(),
            poll_interval=0,
        )

        queued = await service.submit(
            user_id="user@example.com",
            conversation_id="conversation-1",
            message_id=None,
            prompt="A four second tracking shot",
            duration_seconds=4,
        )

        self.assertEqual(queued["duration_seconds"], 3)
        self.assertEqual(client.created[0].duration_seconds, 3)
        await service.wait_for_job(queued["_id"])
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

    async def test_seedance_uses_configured_provider_and_current_message_image(self):
        from AgentBI.src.services.video_generation.service import VideoGenerationService

        self.repository.save_capability_config(
            "user@example.com",
            "tool.video_generation",
            {
                "model": "doubao-seedance-1-0-pro-250528",
                "default_aspect_ratio": "adaptive",
                "default_duration_seconds": 5,
                "resolution": "720p",
                "generate_audio": False,
                "watermark": False,
            },
        )
        agnes = FakeAgnesClient()
        ark = FakeArkProvider()
        assets = FakeAssetService()
        service = VideoGenerationService(
            repository=self.repository,
            providers={"agnes": agnes, "volcengine": ark},
            output_root=Path(self.directory.name),
            asset_service=assets,
            poll_interval=0,
        )

        queued = await service.submit(
            user_id="user@example.com",
            conversation_id="conversation-1",
            message_id=None,
            prompt="The character waves to the camera",
            use_attached_image=True,
            reference_image_data_url="data:image/png;base64,aW1hZ2U=",
        )

        self.assertEqual(queued.get("provider"), "volcengine")
        self.assertEqual(queued.get("model"), "doubao-seedance-1-0-pro-250528")
        self.assertEqual(queued.get("resolution"), "720p")
        self.assertEqual(ark.created[0].image_data_url, "data:image/png;base64,aW1hZ2U=")
        self.assertEqual(ark.created[0].aspect_ratio, "adaptive")
        self.assertEqual(len(agnes.created), 0)

        await service.wait_for_job(queued["_id"])
        completed = service.get_job(queued["_id"], "user@example.com")
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(assets.registered[0]["metadata"]["model"], "doubao-seedance-1-0-pro-250528")
        await service.shutdown()

    async def test_seedance_image_mode_requires_a_current_message_image(self):
        from AgentBI.src.services.video_generation.service import VideoGenerationService

        self.repository.save_capability_config(
            "user@example.com",
            "tool.video_generation",
            {
                "model": "doubao-seedance-1-0-pro-250528",
                "default_aspect_ratio": "16:9",
                "default_duration_seconds": 5,
            },
        )
        service = VideoGenerationService(
            repository=self.repository,
            providers={"volcengine": FakeArkProvider()},
            output_root=Path(self.directory.name),
            asset_service=FakeAssetService(),
            poll_interval=0,
        )

        with self.assertRaisesRegex(ValueError, "附件图片"):
            await service.submit(
                user_id="user@example.com",
                conversation_id="conversation-1",
                message_id=None,
                prompt="Animate it",
                use_attached_image=True,
            )
        await service.shutdown()


if __name__ == "__main__":
    unittest.main()
