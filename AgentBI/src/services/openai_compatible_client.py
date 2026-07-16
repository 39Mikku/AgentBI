import os
from typing import Any

from openai import AsyncOpenAI


def create_openai_compatible_client(provider: dict[str, Any]) -> AsyncOpenAI:
    """Create the shared, business-neutral OpenAI-compatible async client."""

    return AsyncOpenAI(
        api_key=provider["api_key"],
        base_url=provider["base_url"],
        default_headers={
            "User-Agent": os.getenv("LLM_USER_AGENT", "Mozilla/5.0 AgentBI")
        },
    )
