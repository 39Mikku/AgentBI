import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from AgentBI.src.schemas.image_generation_schema import (
    CodexOAuthStartResponse,
    CodexOAuthStatus,
    GeneratedImage,
)


class _Repository:
    def get_provider(self, provider_id):
        if provider_id == "provider-1":
            return {"_id": provider_id, "api_key": "key", "base_url": "https://example.com/v1"}
        return None


class _ImageService:
    async def generate(self, **kwargs):
        self.request = kwargs
        return GeneratedImage(
            id="image-1",
            url="/api/generated-images/hash/direct/image-1.png",
            relative_path="hash/direct/image-1.png",
            media_type="image/png",
            mode="lite",
            model="gemini-image",
            aspect_ratio=kwargs["aspect_ratio"],
            prompt=kwargs["prompt"],
        )


class _OAuthManager:
    def status(self):
        return CodexOAuthStatus(connected=False, pending=False)

    async def start(self):
        return CodexOAuthStartResponse(
            authorization_url="https://auth.openai.com/codex/device",
            user_code="ABCD-EFGH",
            expires_in=900,
        )

    def disconnect(self):
        self.disconnected = True


class ImageGenerationApiTests(unittest.TestCase):
    def setUp(self):
        from AgentBI.src.api.image_generation import router

        app = FastAPI()
        app.include_router(router)
        app.state.chat_repository = _Repository()
        app.state.image_generation_service = _ImageService()
        app.state.codex_image_oauth = _OAuthManager()
        self.app = app
        self.client = TestClient(app)

    def test_direct_generation_preserves_prompt_and_resolves_provider(self):
        response = self.client.post(
            "/image-generation/generate",
            json={
                "user_id": "elysia@example.com",
                "prompt": "原样使用这段描述，不要改写",
                "aspect_ratio": "square",
                "provider_id": "provider-1",
                "scope_id": "assistant-avatar",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.app.state.image_generation_service.request["prompt"],
            "原样使用这段描述，不要改写",
        )
        self.assertEqual(
            self.app.state.image_generation_service.request["provider"]["_id"], "provider-1"
        )

    def test_unknown_provider_is_rejected_without_starting_generation(self):
        response = self.client.post(
            "/image-generation/generate",
            json={
                "user_id": "u",
                "prompt": "prompt",
                "aspect_ratio": "square",
                "provider_id": "missing",
            },
        )

        self.assertEqual(response.status_code, 404)

    def test_oauth_routes_return_status_and_device_code_without_tokens(self):
        status = self.client.get("/image-generation/codex/status").json()
        start = self.client.post("/image-generation/codex/connect").json()
        disconnected = self.client.delete("/image-generation/codex/connection")

        self.assertEqual(status, {"connected": False, "account_id": None, "expires_at": None, "pending": False, "error": None})
        self.assertEqual(start["user_code"], "ABCD-EFGH")
        self.assertNotIn("access_token", str(status) + str(start))
        self.assertEqual(disconnected.status_code, 204)


if __name__ == "__main__":
    unittest.main()
