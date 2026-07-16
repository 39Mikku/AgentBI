import json
import tempfile
import unittest
from pathlib import Path

from AgentBI.src.services.image_generation.lite_adapter import ImageBinary


PNG = b"\x89PNG\r\n\x1a\nservice-image"


class _Repository:
    def __init__(self, config):
        self.config = config

    def get_capability_config(self, user_id, capability_id):
        self.request = (user_id, capability_id)
        return self.config


class _LiteAdapter:
    async def generate(self, **kwargs):
        self.request = kwargs
        return ImageBinary(PNG, "image/png", kwargs["model"])


class _ProAdapter:
    async def generate(self, **kwargs):
        self.request = kwargs
        return ImageBinary(PNG, "image/png", "gpt-image-2")


class _OAuthStore:
    async def valid_access_token(self):
        return "pro-token"


class ImageGenerationServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_lite_uses_current_provider_and_preserves_direct_prompt_verbatim(self):
        from AgentBI.src.services.image_generation.artifact_store import ImageArtifactStore
        from AgentBI.src.services.image_generation.service import ImageGenerationService

        with tempfile.TemporaryDirectory() as directory:
            lite = _LiteAdapter()
            service = ImageGenerationService(
                repository=_Repository(
                    {"mode": "lite", "lite_model": "gemini-image", "pro_quality": "high"}
                ),
                artifact_store=ImageArtifactStore(Path(directory)),
                lite_adapter=lite,
                pro_adapter=_ProAdapter(),
                oauth_store=_OAuthStore(),
            )
            prompt = "像素风白色长发少女，荧光绿背景"

            image = await service.generate(
                user_id="elysia@example.com",
                scope_id="avatar",
                prompt=prompt,
                aspect_ratio="square",
                provider={"api_key": "key", "base_url": "https://newapi.example/v1"},
            )

            self.assertEqual(lite.request["prompt"], prompt)
            self.assertEqual(lite.request["model"], "gemini-image")
            self.assertEqual(image.mode, "lite")
            self.assertTrue((Path(directory) / image.relative_path).exists())

    async def test_lite_requires_a_provider_but_pro_uses_independent_oauth(self):
        from AgentBI.src.services.image_generation.artifact_store import ImageArtifactStore
        from AgentBI.src.services.image_generation.lite_adapter import ImageGenerationError
        from AgentBI.src.services.image_generation.service import ImageGenerationService

        with tempfile.TemporaryDirectory() as directory:
            store = ImageArtifactStore(Path(directory))
            lite_service = ImageGenerationService(
                repository=_Repository(
                    {"mode": "lite", "lite_model": "gemini-image", "pro_quality": "high"}
                ),
                artifact_store=store,
                lite_adapter=_LiteAdapter(),
                pro_adapter=_ProAdapter(),
                oauth_store=_OAuthStore(),
            )
            with self.assertRaisesRegex(ImageGenerationError, "提供商"):
                await lite_service.generate(
                    user_id="u", scope_id="direct", prompt="prompt", aspect_ratio="square"
                )

            pro = _ProAdapter()
            pro_service = ImageGenerationService(
                repository=_Repository(
                    {"mode": "pro", "lite_model": "", "pro_quality": "medium"}
                ),
                artifact_store=store,
                lite_adapter=_LiteAdapter(),
                pro_adapter=pro,
                oauth_store=_OAuthStore(),
            )
            image = await pro_service.generate(
                user_id="u", scope_id="conversation", prompt="prompt", aspect_ratio="landscape"
            )

            self.assertEqual(pro.request["access_token"], "pro-token")
            self.assertEqual(pro.request["quality"], "medium")
            self.assertEqual(image.model, "gpt-image-2")

    async def test_atomic_tool_returns_compact_context_and_image_card(self):
        from AgentBI.src.schemas.image_generation_schema import GeneratedImage
        from AgentBI.src.tools.image_generation_tools import generate_image

        class Service:
            async def generate(self, **kwargs):
                self.request = kwargs
                return GeneratedImage(
                    id="image-1",
                    url="/api/generated-images/hash/chat/image-1.png",
                    relative_path="hash/chat/image-1.png",
                    media_type="image/png",
                    mode="lite",
                    model="gemini-image",
                    aspect_ratio="portrait",
                    prompt=kwargs["prompt"],
                )

        service = Service()
        result = await generate_image(
            service,
            user_id="user",
            scope_id="chat",
            prompt="planned prompt",
            aspect_ratio="portrait",
            provider={"id": "provider"},
        )

        self.assertEqual(service.request["prompt"], "planned prompt")
        self.assertIn("image-1", result.content)
        self.assertNotIn("base64", result.content.lower())
        self.assertNotIn("/api/generated-images/", result.content)
        self.assertTrue(json.loads(result.content)["image_attached"])
        self.assertEqual(result.card["kind"], "image.generated")
        self.assertEqual(result.card["payload"]["url"], "/api/generated-images/hash/chat/image-1.png")


if __name__ == "__main__":
    unittest.main()
