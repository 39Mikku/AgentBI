from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.openai_compatible_client import create_openai_compatible_client


class ModelTaskConfigurationError(RuntimeError):
    """Raised when the selected Studio chat model cannot be resolved."""


class ModelTaskEmptyResponseError(RuntimeError):
    """Raised when a model call succeeds without usable text."""


@dataclass(frozen=True)
class ModelTaskResult:
    text: str
    provider_name: str
    model: str


class ModelTaskService:
    """Small OpenAI-compatible client for non-streaming background model roles."""

    def __init__(self, repository: SqliteChatRepository):
        self.repository = repository

    @staticmethod
    def _client(provider: dict[str, Any]) -> AsyncOpenAI:
        return create_openai_compatible_client(provider)

    def resolve(self, user_id: str, role: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        route = self.repository.get_model_route(user_id, role)
        provider = self.repository.get_provider(route["provider_id"]) if route else None
        return (route, provider) if route and provider else None

    async def complete(self, user_id: str, role: str, system: str, prompt: str) -> str | None:
        resolved = self.resolve(user_id, role)
        if not resolved:
            return None
        route, provider = resolved
        response = await self._client(provider).chat.completions.create(
            model=route["model"],
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            temperature=1.0,
        )
        content = response.choices[0].message.content if response.choices else None
        return content.strip() if content else None

    async def complete_with_chat_preferences(
        self, user_id: str, system: str, prompt: str
    ) -> ModelTaskResult:
        preferences = self.repository.get_preferences(user_id)
        provider = self.repository.get_provider(preferences.get("provider_id"))
        if not provider:
            raise ModelTaskConfigurationError("请先在 Studio 模型配置中选择提供商")

        model = preferences.get("model") or provider.get("default_model")
        if not model:
            raise ModelTaskConfigurationError("请先在 Studio 模型配置中选择聊天模型")

        response = await self._client(provider).chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            temperature=preferences.get("temperature", 1.0),
        )
        content = response.choices[0].message.content if response.choices else None
        text = content.strip() if content else ""
        if not text:
            raise ModelTaskEmptyResponseError("模型未返回可用文案")

        return ModelTaskResult(
            text=text,
            provider_name=provider.get("name") or "未命名提供商",
            model=model,
        )

    async def embed(self, user_id: str, texts: list[str]) -> tuple[str, list[list[float]]] | None:
        resolved = self.resolve(user_id, "embedding")
        if not resolved or not texts:
            return None
        route, provider = resolved
        response = await self._client(provider).embeddings.create(model=route["model"], input=texts)
        vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        return f"{route['provider_id']}:{route['model']}", vectors
