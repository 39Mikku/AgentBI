import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from AgentBI.src.tools.send_email_tool import send_email
from AgentBI.src.tools.mongo_query_tool import mongo_query


class EmailAgent:
    """邮件发送子代理，复用旧邮件助手的撰写与发送职责。"""

    system_prompt = (
        "你是邮件发送子代理。根据用户请求及主代理提供的查询结果，"
        "整理准确、清晰的邮件主题和正文，然后调用 send_email 发送。"
        "收件人仅给出 username 或姓名时，先在 users 集合查询 username/email；"
        "若必要信息仍不足，直接说明缺失的信息。"
        "发送后用一句简短的话确认结果。"
    )

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        return [{
            "type": "function",
            "function": {
                "name": "mongo_query",
                "description": "查询 users 集合以取得收件人的邮箱地址。query 必须为 JSON 字符串。",
                "parameters": {
                    "type": "object",
                    "properties": {"collection": {"type": "string"}, "query": {"type": "string"}},
                    "required": ["collection", "query"],
                },
            },
        }, {
            "type": "function",
            "function": {
                "name": "send_email",
                "description": "发送已经整理好的邮件。",
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
        }]

    async def stream(
        self,
        client: AsyncOpenAI,
        model: str,
        temperature: float,
        instruction: str,
    ) -> AsyncIterator[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": instruction},
        ]
        for _ in range(3):
            content_parts: list[str] = []
            tool_calls: dict[int, dict[str, str]] = {}
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True,
                tools=self.tool_definitions(),
            )
            async for chunk in response:
                choice = chunk.choices[0] if chunk.choices else None
                if not choice:
                    continue
                delta = choice.delta
                if delta.content:
                    content_parts.append(delta.content)
                    yield {"type": "delta", "content": delta.content}
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    yield {"type": "reasoning_summary", "content": reasoning}
                for tool_call in delta.tool_calls or []:
                    entry = tool_calls.setdefault(tool_call.index, {"id": "", "name": "", "arguments": ""})
                    if tool_call.id:
                        entry["id"] = tool_call.id
                    if tool_call.function and tool_call.function.name:
                        entry["name"] = tool_call.function.name
                    if tool_call.function and tool_call.function.arguments:
                        entry["arguments"] += tool_call.function.arguments

            if not tool_calls:
                return
            messages.append({
                "role": "assistant",
                "content": "".join(content_parts) or None,
                "tool_calls": [{
                    "id": call["id"],
                    "type": "function",
                    "function": {"name": call["name"], "arguments": call["arguments"]},
                } for call in tool_calls.values()],
            })
            for call in tool_calls.values():
                yield {"type": "tool_started", "tool": call["name"]}
                result = self._invoke_tool(call["name"], call["arguments"])
                yield {"type": "tool_finished", "tool": call["name"], "content": result}
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    @staticmethod
    def _invoke_tool(name: str, arguments: str) -> str:
        try:
            payload = json.loads(arguments or "{}")
            if name == "mongo_query":
                return str(mongo_query.invoke(payload))
            if name == "send_email":
                return str(send_email.invoke(payload))
            return f"未知邮件工具: {name}"
        except Exception as error:
            return f"邮件发送失败: {error}"
