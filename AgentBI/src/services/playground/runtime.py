from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from AgentBI.src.services.model_reasoning import model_reasoning_request_options
from AgentBI.src.services.openai_compatible_client import create_openai_compatible_client
from AgentBI.src.services.playground.structured_output import StructuredTailParser


class PlaygroundRuntime:
    """A deliberately tool-free streaming model runtime for roleplay."""

    async def stream(
        self,
        *,
        messages: list[dict[str, Any]],
        provider: dict[str, Any],
        model: str,
        temperature: float,
        thinking_level: str,
        expect_state: bool,
        expect_options: bool,
        variable_definitions: list[dict[str, Any]] | None = None,
        previous_state: dict[str, Any] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        request: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        request.update(model_reasoning_request_options(model, thinking_level))
        response = await create_openai_compatible_client(provider).chat.completions.create(**request)
        parser = StructuredTailParser(
            expect_state=expect_state,
            expect_options=expect_options,
            variable_definitions=variable_definitions,
            previous_state=previous_state,
        )
        async for chunk in response:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue
            delta = choice.delta
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield {"type": "reasoning_summary", "content": reasoning}
            content = getattr(delta, "content", None)
            if content:
                visible = parser.feed(content)
                if visible:
                    yield {"type": "delta", "content": visible}
        result = parser.finish()
        if result.visible_tail:
            yield {"type": "delta", "content": result.visible_tail}
        yield {"type": "structured", "result": result}
