from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import httpx

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


class TavilySearchError(RuntimeError):
    pass


class TavilySearchClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 20,
    ) -> None:
        self.api_key = (api_key if api_key is not None else os.getenv("TAVILY_API_KEY", "")).strip()
        self.http_client = http_client
        self.timeout = timeout

    async def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        search_depth: str = "basic",
        topic: str = "general",
        time_range: str | None = None,
    ) -> dict[str, Any]:
        normalized_query = query.strip()
        if not normalized_query:
            raise TavilySearchError("请提供网页搜索关键词")
        if not self.api_key:
            raise TavilySearchError("Tavily API Key 未配置")
        payload: dict[str, Any] = {
            "query": normalized_query,
            "max_results": min(max(int(max_results), 1), 20),
            "search_depth": search_depth if search_depth in {"ultra-fast", "fast", "basic", "advanced"} else "basic",
            "topic": topic if topic in {"general", "news", "finance"} else "general",
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "auto_parameters": False,
        }
        if time_range in {"day", "week", "month", "year"}:
            payload["time_range"] = time_range
        try:
            response = await self._post(payload)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise TavilySearchError("Tavily 搜索请求失败") from error
        if not isinstance(data, Mapping):
            raise TavilySearchError("Tavily 返回了无效搜索结果")
        results = []
        for item in data.get("results", []):
            if not isinstance(item, Mapping) or not item.get("url"):
                continue
            results.append({
                "title": str(item.get("title") or "未命名来源"),
                "url": str(item["url"]),
                "content": str(item.get("content") or ""),
                "score": float(item.get("score") or 0),
                **({"published_date": str(item["published_date"])} if item.get("published_date") else {}),
            })
        return {"query": str(data.get("query") or normalized_query), "results": results}

    async def _post(self, payload: dict[str, Any]):
        options = {
            "json": payload,
            "headers": {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            "timeout": self.timeout,
        }
        if self.http_client is not None:
            return await self.http_client.post(TAVILY_SEARCH_URL, **options)
        async with httpx.AsyncClient() as client:
            return await client.post(TAVILY_SEARCH_URL, **options)
