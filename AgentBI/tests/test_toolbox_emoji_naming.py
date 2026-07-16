import asyncio
import base64
import unittest

from AgentBI.src.services.model_task_service import ModelTaskResult


PNG_DATA_URL = "data:image/png;base64," + base64.b64encode(
    b"\x89PNG\r\n\x1a\nemoji"
).decode("ascii")


class _BatchTasks:
    def __init__(self):
        self.calls = []

    async def complete_vision(self, user_id, system, prompt, images):
        self.calls.append((user_id, system, prompt, images))
        return ModelTaskResult(
            text='```json\n{"names":[{"id":"s1","name":"开心挥手！"},{"id":"s2","name":"无语扶额"}]}\n```',
            provider_name="NewAPI",
            model="vision-mini",
        )


class _IndividualTasks:
    def __init__(self):
        self.calls = []
        self.active = 0
        self.max_active = 0

    async def complete_vision(self, user_id, system, prompt, images):
        self.calls.append(images[0]["id"])
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        return ModelTaskResult(
            text='{"name":"开心挥手"}',
            provider_name="NewAPI",
            model="vision-mini",
        )


class StickerNamingServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_batch_parses_fenced_json_and_returns_safe_chinese_names_in_input_order(self):
        from AgentBI.src.services.toolbox.emoji_naming import StickerNamingService

        tasks = _BatchTasks()
        result = await StickerNamingService(tasks).name(
            user_id="user-1",
            strategy="batch",
            images=[
                {"id": "s1", "data_url": PNG_DATA_URL},
                {"id": "s2", "data_url": PNG_DATA_URL},
            ],
        )

        self.assertEqual([item.name for item in result.names], ["开心挥手", "无语扶额"])
        self.assertEqual(result.strategy, "batch")
        self.assertEqual(result.model, "vision-mini")
        self.assertEqual(len(tasks.calls), 1)
        self.assertIn("只使用简短中文", tasks.calls[0][2])

    async def test_individual_strategy_sends_one_image_per_call_with_bounded_concurrency(self):
        from AgentBI.src.services.toolbox.emoji_naming import StickerNamingService

        tasks = _IndividualTasks()
        images = [{"id": f"s{index}", "data_url": PNG_DATA_URL} for index in range(7)]
        result = await StickerNamingService(tasks, max_concurrency=3).name(
            user_id="user-1",
            strategy="individual",
            images=images,
        )

        self.assertEqual(len(tasks.calls), 7)
        self.assertLessEqual(tasks.max_active, 3)
        self.assertEqual([item.id for item in result.names], [item["id"] for item in images])
        self.assertTrue(all(item.name == "开心挥手" for item in result.names))

    async def test_missing_or_non_chinese_names_use_stable_chinese_fallbacks(self):
        class Tasks:
            async def complete_vision(self, *args, **kwargs):
                return ModelTaskResult(
                    text='{"names":[{"id":"s1","name":"happy_wave"}]}',
                    provider_name="NewAPI",
                    model="vision-mini",
                )

        from AgentBI.src.services.toolbox.emoji_naming import StickerNamingService

        result = await StickerNamingService(Tasks()).name(
            user_id="user-1",
            strategy="batch",
            images=[
                {"id": "s1", "data_url": PNG_DATA_URL},
                {"id": "s2", "data_url": PNG_DATA_URL},
            ],
        )

        self.assertEqual([item.name for item in result.names], ["表情01", "表情02"])


if __name__ == "__main__":
    unittest.main()
