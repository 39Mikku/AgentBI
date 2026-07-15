import unittest
from types import SimpleNamespace
from unittest.mock import patch


class _Repository:
    def get_model_route(self, user_id, role):
        return {"provider_id": "provider-1", "model": "task-model"}

    def get_provider(self, provider_id):
        return {"api_key": "test", "base_url": "https://example.invalid/v1"}


class _Completions:
    def __init__(self):
        self.request = None

    async def create(self, **request):
        self.request = request
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="result"))])


class ModelTaskServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_background_models_use_provider_recommended_default_temperature(self):
        from AgentBI.src.services.model_task_service import ModelTaskService

        completions = _Completions()
        client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        with patch.object(ModelTaskService, "_client", return_value=client):
            result = await ModelTaskService(_Repository()).complete("user", "memory", "system", "prompt")

        self.assertEqual(result, "result")
        self.assertEqual(completions.request["temperature"], 1.0)


if __name__ == "__main__":
    unittest.main()
