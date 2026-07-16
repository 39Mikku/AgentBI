import base64
import json
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

    async def describe_images(
        self, user_id: str, images: list[dict[str, Any]]
    ) -> dict[str, str] | None:
        resolved = self.resolve(user_id, "vision")
        if not resolved or not images:
            return None
        route, provider = resolved
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "请逐张识别这些图片，完整转述文字、主体、布局、图表和与后续对话有关的细节。"
                    "只返回 JSON 数组，每项包含 id 和 description。图片标签如下：\n"
                    + "\n".join(f"{item['id']}: {item['filename']}" for item in images)
                ),
            }
        ]
        for item in images:
            encoded = base64.b64encode(item["data"]).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{item['mime_type']};base64,{encoded}"},
                }
            )
        response = await self._client(provider).chat.completions.create(
            model=route["model"],
            messages=[
                {"role": "system", "content": "你是图像内容转述模型。"},
                {"role": "user", "content": content},
            ],
            temperature=1.0,
        )
        text = response.choices[0].message.content.strip() if response.choices else ""
        if not text:
            raise ModelTaskEmptyResponseError("识图模型未返回可用转述")
        try:
            raw = text.strip().removeprefix("```json").removesuffix("```").strip()
            parsed = json.loads(raw)
            result = {
                str(item["id"]): str(item["description"]).strip()
                for item in parsed
                if isinstance(item, dict) and item.get("id") and item.get("description")
            }
        except (TypeError, ValueError, json.JSONDecodeError):
            result = {}
        if not result:
            result = {str(item["id"]): text for item in images}
        return result
