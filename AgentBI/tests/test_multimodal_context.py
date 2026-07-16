import tempfile
import unittest
from pathlib import Path

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.studio_asset_service import StudioAssetService


PNG = b"\x89PNG\r\n\x1a\n" + b"multimodal"


class _VisionTasks:
    def __init__(self, descriptions=None):
        self.descriptions = descriptions
        self.calls = []

    async def describe_images(self, user_id, images):
        self.calls.append((user_id, images))
        return self.descriptions


class MultimodalContextTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.repository = SqliteChatRepository(":memory:")
        self.assets = StudioAssetService(self.repository, Path(self.directory.name))
        self.provider = self.repository.create_provider(
            {
                "name": "Provider", "base_url": "https://example.invalid/v1",
                "api_key": "key", "default_model": "chat-model",
            }
        )
        assistant = self.repository.ensure_default_assistant("user-1")
        self.thread = self.repository.create_conversation(
            {
                "user_id": "user-1", "title": "multimodal", "temperature": 1.0,
                "context_turns": 8, "assistant_id": assistant["_id"],
            }
        )
        self.message = self.repository.create_user_message(
            self.thread["_id"], "user-1", "这张图是什么？"
        )
        self.asset = self.assets.upload(
            user_id="user-1", filename="diagram.png", content_type="image/png", data=PNG
        )
        self.assets.bind_assets(self.message["_id"], "user-1", [self.asset["_id"]])

    async def asyncTearDown(self):
        self.repository.close()
        self.directory.cleanup()

    async def test_visual_chat_model_receives_original_image_without_vision_route(self):
        from AgentBI.src.services.multimodal_context_service import MultimodalContextService

        self.repository.set_model_capability(
            "user-1", self.provider["_id"], "chat-model", supports_vision=True
        )
        tasks = _VisionTasks()
        service = MultimodalContextService(self.repository, self.assets, tasks)

        prepared = await service.prepare(
            user_id="user-1",
            provider_id=self.provider["_id"],
            model="chat-model",
            context=[{"role": "user", "content": "这张图是什么？"}],
            path=self.repository.get_active_path(self.thread["_id"], "user-1"),
        )

        content = prepared[0]["content"]
        self.assertIsInstance(content, list)
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(tasks.calls, [])

    async def test_text_model_uses_and_caches_hidden_vision_summary(self):
        from AgentBI.src.services.multimodal_context_service import MultimodalContextService

        tasks = _VisionTasks({self.asset["_id"]: "包含三个模块的系统架构图"})
        service = MultimodalContextService(self.repository, self.assets, tasks)
        kwargs = dict(
            user_id="user-1",
            provider_id=self.provider["_id"],
            model="chat-model",
            context=[{"role": "user", "content": "这张图是什么？"}],
            path=self.repository.get_active_path(self.thread["_id"], "user-1"),
        )

        first = await service.prepare(**kwargs)
        second = await service.prepare(**kwargs)

        self.assertIn("包含三个模块的系统架构图", first[0]["content"])
        self.assertIn("<image_attachment", first[0]["content"])
        self.assertEqual(len(tasks.calls), 1)
        self.assertEqual(first, second)

    async def test_text_model_requires_configured_vision_route(self):
        from AgentBI.src.services.model_task_service import ModelTaskConfigurationError
        from AgentBI.src.services.multimodal_context_service import MultimodalContextService

        service = MultimodalContextService(self.repository, self.assets, _VisionTasks(None))
        with self.assertRaisesRegex(ModelTaskConfigurationError, "识图模型"):
            await service.prepare(
                user_id="user-1",
                provider_id=self.provider["_id"],
                model="chat-model",
                context=[{"role": "user", "content": "这张图是什么？"}],
                path=self.repository.get_active_path(self.thread["_id"], "user-1"),
            )


if __name__ == "__main__":
    unittest.main()
