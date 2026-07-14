from typing import Any

import httpx

from AgentBI.src.repositories.chat_repository import ChatRepository


def normalize_model_ids(payload: dict[str, Any]) -> list[str]:
    records = payload.get("data", []) if isinstance(payload, dict) else []
    model_ids = {
        item.get("id").strip()
        for item in records
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id").strip()
    }
    return sorted(model_ids)


class ProviderService:
    def __init__(self, repository: ChatRepository, client: httpx.AsyncClient | None = None):
        self.repository = repository
        self.client = client

    async def refresh_models(self, provider_id: str) -> dict[str, Any] | None:
        provider = self.repository.get_provider(provider_id)
        if not provider:
            return None
        url = f"{provider['base_url'].rstrip('/')}/models"
        headers = {"Authorization": f"Bearer {provider['api_key']}"}
        if self.client:
            response = await self.client.get(url, headers=headers)
        else:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get(url, headers=headers)
        response.raise_for_status()
        models = normalize_model_ids(response.json())
        return self.repository.update_provider(provider_id, {"available_models": models})

