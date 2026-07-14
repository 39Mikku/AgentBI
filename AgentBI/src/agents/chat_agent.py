import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from AgentBI.src.tools.mongo_query_tool import mongo_query
from AgentBI.src.tools.send_email_tool import send_email


class ChatAgent:
    system_prompt = (
        "你是 AgentBI 的工作台助手。回答应清晰、直接。"
        "在用户明确要求查询数据库或发送邮件时，直接调用对应工具并简洁说明执行结果。"
    )

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "mongo_query",
                    "description": "查询 MongoDB 集合。query 必须是 JSON 字符串。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "collection": {"type": "string"},
                            "query": {"type": "string"},
                        },
                        "required": ["collection", "query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "向指定邮箱发送一封邮件。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "to": {"type": "string"},
                            "subject": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["to", "subject", "content"],
                    },
                },
            },
        ]

    async def stream(
        self,
        messages: list[dict[str, str]],
        provider: dict[str, Any],
        model: str,
        temperature: float,
    ) -> AsyncIterator[dict[str, Any]]:
        client = AsyncOpenAI(api_key=provider["api_key"], base_url=provider["base_url"])
        request_messages = [{"role": "system", "content": self.system_prompt}, *messages]
        async for event in self._stream_completion(client, request_messages, model, temperature):
            yield event

    async def _stream_completion(
        self,
        client: AsyncOpenAI,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float,
    ) -> AsyncIterator[dict[str, Any]]:
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=True,
            tools=self.tool_definitions(),
        )
        tool_calls: dict[int, dict[str, Any]] = {}
        async for chunk in stream:
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue
            delta = choice.delta
            if delta.content:
                yield {"type": "delta", "content": delta.content}
            reasoning = getattr(delta, "reasoning_content", None)
            if reasoning:
                yield {"type": "reasoning_summary", "content": reasoning}
            for tool_call in delta.tool_calls or []:
                entry = tool_calls.setdefault(
                    tool_call.index,
                    {"id": "", "name": "", "arguments": ""},
                )
                if tool_call.id:
                    entry["id"] = tool_call.id
                if tool_call.function and tool_call.function.name:
                    entry["name"] = tool_call.function.name
                if tool_call.function and tool_call.function.arguments:
                    entry["arguments"] += tool_call.function.arguments
        for call in tool_calls.values():
            yield {"type": "tool_started", "tool": call["name"]}
            result = self._invoke_tool(call["name"], call["arguments"])
            yield {"type": "tool_finished", "tool": call["name"], "content": result}

    @staticmethod
    def _invoke_tool(name: str, arguments: str) -> str:
        try:
            payload = json.loads(arguments or "{}")
            if name == "mongo_query":
                return str(mongo_query.invoke(payload))
            if name == "send_email":
                return str(send_email.invoke(payload))
            return f"未知工具: {name}"
        except Exception as error:
            return f"工具执行失败: {error}"
