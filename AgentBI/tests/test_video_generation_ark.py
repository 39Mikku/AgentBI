import json
import unittest

import httpx


class ArkVideoClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_text_to_video_uses_strongly_typed_body_parameters(self):
        from AgentBI.src.services.video_generation.ark_client import ArkVideoClient
        from AgentBI.src.services.video_generation.provider import VideoCreateRequest

        captured = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "cgt-1"})

        http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://ark.example.test/api/v3",
        )
        client = ArkVideoClient("secret", http_client=http)
        try:
            result = await client.create_video(
                VideoCreateRequest(
                    prompt="A paper kite crossing the sea",
                    model="doubao-seedance-1-0-pro-250528",
                    aspect_ratio="16:9",
                    duration_seconds=5,
                    resolution="1080p",
                    generate_audio=True,
                    watermark=False,
                )
            )
        finally:
            await http.aclose()

        self.assertEqual(result.get("task_id"), "cgt-1")
        self.assertEqual(
            captured,
            {
                "model": "doubao-seedance-1-0-pro-250528",
                "content": [{"type": "text", "text": "A paper kite crossing the sea"}],
                "ratio": "16:9",
                "duration": 5,
                "resolution": "1080p",
                "generate_audio": True,
                "watermark": False,
            },
        )

    async def test_create_image_to_video_appends_image_data_url(self):
        from AgentBI.src.services.video_generation.ark_client import ArkVideoClient
        from AgentBI.src.services.video_generation.provider import VideoCreateRequest

        captured = {}

        async def handler(request: httpx.Request) -> httpx.Response:
            captured.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "cgt-image"})

        http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://ark.example.test/api/v3",
        )
        client = ArkVideoClient("secret", http_client=http)
        try:
            await client.create_video(
                VideoCreateRequest(
                    prompt="The character waves",
                    model="doubao-seedance-1-0-pro-250528",
                    aspect_ratio="adaptive",
                    duration_seconds=6,
                    image_data_url="data:image/png;base64,aW1hZ2U=",
                )
            )
        finally:
            await http.aclose()

        self.assertEqual(
            captured.get("content", [None, None])[1],
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64,aW1hZ2U="},
            },
        )

    async def test_query_normalizes_status_and_nested_video_url(self):
        from AgentBI.src.services.video_generation.ark_client import ArkVideoClient

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": "cgt-1",
                    "model": "doubao-seedance-1-0-pro-250528",
                    "status": "succeeded",
                    "content": {"video_url": "https://cdn.example.test/video.mp4"},
                    "duration": 6,
                    "ratio": "16:9",
                    "resolution": "1080p",
                    "generate_audio": True,
                },
            )

        http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://ark.example.test/api/v3",
        )
        client = ArkVideoClient("secret", http_client=http)
        try:
            result = await client.get_video("cgt-1")
        finally:
            await http.aclose()

        self.assertEqual(result.get("status"), "completed")
        self.assertEqual(result.get("url"), "https://cdn.example.test/video.mp4")
        self.assertEqual(result.get("metadata", {}).get("resolution"), "1080p")

    async def test_expired_and_cancelled_are_terminal_failures(self):
        from AgentBI.src.services.video_generation.ark_client import ArkVideoClient

        statuses = iter(("expired", "cancelled"))

        async def handler(request: httpx.Request) -> httpx.Response:
            status = next(statuses)
            return httpx.Response(200, json={"id": "cgt-1", "status": status})

        http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://ark.example.test/api/v3",
        )
        client = ArkVideoClient("secret", http_client=http)
        try:
            self.assertEqual((await client.get_video("cgt-1")).get("status"), "failed")
            self.assertEqual((await client.get_video("cgt-1")).get("status"), "failed")
        finally:
            await http.aclose()

    async def test_rate_limit_error_is_retryable(self):
        from AgentBI.src.services.video_generation.ark_client import ArkVideoClient, ArkVideoError
        from AgentBI.src.services.video_generation.provider import VideoCreateRequest

        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": {"message": "busy"}})

        http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://ark.example.test/api/v3",
        )
        client = ArkVideoClient("secret", http_client=http)
        try:
            with self.assertRaises(ArkVideoError) as raised:
                await client.create_video(
                    VideoCreateRequest(
                        prompt="A lake",
                        model="doubao-seedance-1-0-pro-250528",
                        aspect_ratio="16:9",
                        duration_seconds=5,
                    )
                )
        finally:
            await http.aclose()

        self.assertTrue(raised.exception.retryable)


if __name__ == "__main__":
    unittest.main()
