from __future__ import annotations

import json
from typing import Any

from AgentBI.src.services.tavily_search_client import TavilySearchClient


async def search_web(
    client: TavilySearchClient,
    query: str,
    config: dict[str, Any],
    *,
    topic: str = "general",
    time_range: str | None = None,
) -> str:
    result = await client.search(
        query,
        max_results=int(config.get("max_results", 5)),
        search_depth=str(config.get("search_depth", "basic")),
        topic=topic,
        time_range=time_range,
    )
    return json.dumps(result, ensure_ascii=False)
