import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository


class ModelCapabilityRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repository = SqliteChatRepository(":memory:")
        self.provider = self.repository.create_provider(
            {
                "name": "Provider",
                "base_url": "https://example.invalid/v1",
                "api_key": "key",
                "default_model": "vision-model",
            }
        )

    def tearDown(self):
        self.repository.close()

    def test_capability_is_bound_to_exact_user_provider_and_model(self):
        self.assertFalse(
            self.repository.model_supports_vision("user-1", self.provider["_id"], "vision-model")
        )

        saved = self.repository.set_model_capability(
            "user-1", self.provider["_id"], "vision-model", supports_vision=True
        )

        self.assertTrue(saved["supports_vision"])
        self.assertTrue(
            self.repository.model_supports_vision("user-1", self.provider["_id"], "vision-model")
        )
        self.assertFalse(
            self.repository.model_supports_vision("user-2", self.provider["_id"], "vision-model")
        )
        self.assertFalse(
            self.repository.model_supports_vision("user-1", self.provider["_id"], "text-model")
        )

    def test_deleting_provider_removes_capabilities(self):
        self.repository.set_model_capability(
            "user-1", self.provider["_id"], "vision-model", supports_vision=True
        )
        self.repository.delete_provider(self.provider["_id"])
        self.assertEqual(self.repository.list_model_capabilities("user-1"), [])


class _Completions:
    def __init__(self):
        self.request = None

    async def create(self, **request):
        self.request = request
        content = json.dumps(
            [
                {"id": "image-1", "description": "第一张图"},
                {"id": "image-2", "description": "第二张图"},
            ],
            ensure_ascii=False,
        )
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class _VisionRepository:
    def get_model_route(self, user_id, role):
        return {"provider_id": "provider-1", "model": "vision-model"} if role == "vision" else None

    def get_provider(self, provider_id):
        return {
            "_id": provider_id,
            "name": "Provider",
            "api_key": "key",
            "base_url": "https://example.invalid/v1",
        }


class VisionModelTaskTests(unittest.IsolatedAsyncioTestCase):
    async def test_describes_multiple_images_in_one_temperature_one_request(self):
        from AgentBI.src.services.model_task_service import ModelTaskService

        completions = _Completions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        with patch.object(ModelTaskService, "_client", return_value=client):
            result = await ModelTaskService(_VisionRepository()).describe_images(
                "user-1",
                [
                    {"id": "image-1", "filename": "one.png", "mime_type": "image/png", "data": b"one"},
                    {"id": "image-2", "filename": "two.png", "mime_type": "image/png", "data": b"two"},
                ],
            )

        request = completions.request
        content = request["messages"][1]["content"]
        self.assertEqual(request["temperature"], 1.0)
        self.assertEqual(sum(item["type"] == "image_url" for item in content), 2)
        self.assertEqual(result, {"image-1": "第一张图", "image-2": "第二张图"})


if __name__ == "__main__":
    unittest.main()
