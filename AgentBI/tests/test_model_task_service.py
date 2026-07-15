import unittest
from types import SimpleNamespace
from unittest.mock import patch


class _Repository:
    def __init__(self):
        self.preferences = {
            "provider_id": "provider-1",
            "model": "chat-model",
            "temperature": 0.9,
        }

    def get_model_route(self, user_id, role):
        return {"provider_id": "provider-1", "model": "task-model"}

    def get_provider(self, provider_id):
        if not provider_id:
            return None
        return {
            "api_key": "test",
            "base_url": "https://example.invalid/v1",
            "name": "NewAPI",
            "default_model": "default-model",
        }

    def get_preferences(self, user_id):
        return self.preferences


class _Completions:
    def __init__(self):
        self.request = None

    async def create(self, **request):
        self.request = request
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="result"))])


class _EmptyCompletions(_Completions):
    async def create(self, **request):
        self.request = request
        return SimpleNamespace(choices=[])


class ModelTaskServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_background_models_use_provider_recommended_default_temperature(self):
        from AgentBI.src.services.model_task_service import ModelTaskService

        completions = _Completions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        with patch.object(ModelTaskService, "_client", return_value=client):
            result = await ModelTaskService(_Repository()).complete("user", "memory", "system", "prompt")

        self.assertEqual(result, "result")
        self.assertEqual(completions.request["temperature"], 1.0)

    async def test_chat_preference_completion_reuses_provider_model_and_temperature(self):
        from AgentBI.src.services.model_task_service import ModelTaskService

        completions = _Completions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        with patch.object(ModelTaskService, "_client", return_value=client):
            result = await ModelTaskService(_Repository()).complete_with_chat_preferences(
                "alice", "system", "prompt"
            )

        self.assertEqual(result.text, "result")
        self.assertEqual(result.provider_name, "NewAPI")
        self.assertEqual(result.model, "chat-model")
        self.assertEqual(completions.request["model"], "chat-model")
        self.assertEqual(completions.request["temperature"], 0.9)
        self.assertEqual(
            completions.request["messages"],
            [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "prompt"},
            ],
        )

    async def test_chat_preference_completion_uses_provider_default_model(self):
        from AgentBI.src.services.model_task_service import ModelTaskService

        repository = _Repository()
        repository.preferences["model"] = None
        completions = _Completions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        with patch.object(ModelTaskService, "_client", return_value=client):
            result = await ModelTaskService(repository).complete_with_chat_preferences(
                "alice", "system", "prompt"
            )

        self.assertEqual(result.model, "default-model")
        self.assertEqual(completions.request["model"], "default-model")

    async def test_chat_preference_completion_rejects_missing_provider(self):
        from AgentBI.src.services.model_task_service import (
            ModelTaskConfigurationError,
            ModelTaskService,
        )

        repository = _Repository()
        repository.preferences["provider_id"] = None

        with self.assertRaises(ModelTaskConfigurationError):
            await ModelTaskService(repository).complete_with_chat_preferences(
                "alice", "system", "prompt"
            )

    async def test_chat_preference_completion_rejects_empty_response(self):
        from AgentBI.src.services.model_task_service import (
            ModelTaskEmptyResponseError,
            ModelTaskService,
        )

        completions = _EmptyCompletions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        with patch.object(ModelTaskService, "_client", return_value=client):
            with self.assertRaises(ModelTaskEmptyResponseError):
                await ModelTaskService(_Repository()).complete_with_chat_preferences(
                    "alice", "system", "prompt"
                )


if __name__ == "__main__":
    unittest.main()
