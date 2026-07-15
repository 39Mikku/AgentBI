import os
from typing import Any

from openai import AsyncOpenAI

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository


class ModelTaskService:
    """Small OpenAI-compatible client for non-streaming background model roles."""

    def __init__(self, repository: SqliteChatRepository):
        self.repository = repository

    @staticmethod
    def _client(provider: dict[str, Any]) -> AsyncOpenAI:
        return AsyncOpenAI(
            api_key=provider["api_key"],
            base_url=provider["base_url"],
            default_headers={"User-Agent": os.getenv("LLM_USER_AGENT", "Mozilla/5.0 AgentBI")},
        )

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

    async def embed(self, user_id: str, texts: list[str]) -> tuple[str, list[list[float]]] | None:
        resolved = self.resolve(user_id, "embedding")
        if not resolved or not texts:
            return None
        route, provider = resolved
        response = await self._client(provider).embeddings.create(model=route["model"], input=texts)
        vectors = [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
        return f"{route['provider_id']}:{route['model']}", vectors
