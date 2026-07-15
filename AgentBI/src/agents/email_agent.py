import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.tools.send_email_tool import send_email


class EmailAgent:
    """Email subagent with a deliberately restricted local recipient lookup."""

    system_prompt = (
        "You are an email delivery subagent. Compose a clear email from the user's request, "
        "look up a recipient only when they give a username or email, then call send_email. "
        "If recipient information is still missing, state exactly what is needed."
    )

    def __init__(
        self,
        repository: SqliteChatRepository | None = None,
        settings: dict[str, Any] | None = None,
    ):
        self.repository = repository

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "lookup_recipient",
                    "description": "Find one local recipient by username or email and return the matching email address.",
                    "parameters": {
                        "type": "object",
                        "properties": {"identity": {"type": "string"}},
                        "required": ["identity"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "send_email",
                    "description": "Send a composed email to a confirmed email address.",
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

    async def stream(self, client: AsyncOpenAI, model: str, temperature: float, instruction: str) -> AsyncIterator[dict[str, Any]]:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": instruction},
        ]
        for _ in range(3):
            content_parts: list[str] = []
            tool_calls: dict[int, dict[str, str]] = {}
            response = await client.chat.completions.create(model=model, messages=messages, temperature=temperature, stream=True, tools=self.tool_definitions())
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
                "tool_calls": [{"id": call["id"], "type": "function", "function": {"name": call["name"], "arguments": call["arguments"]}} for call in tool_calls.values()],
            })
            for call in tool_calls.values():
                yield {"type": "tool_started", "tool": call["name"]}
                result = self._invoke_tool(call["name"], call["arguments"])
                yield {"type": "tool_finished", "tool": call["name"], "content": result}
                messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    def _invoke_tool(self, name: str, arguments: str) -> str:
        try:
            payload = json.loads(arguments or "{}")
            if name == "lookup_recipient":
                recipient = self.repository.find_user(str(payload.get("identity", ""))) if self.repository else None
                if not recipient:
                    return "未找到对应收件人，请提供准确的用户名或邮箱。"
                return json.dumps({"username": recipient["username"], "email": recipient["email"]}, ensure_ascii=False)
            if name == "send_email":
                return str(send_email.invoke(payload))
            return f"未知邮件工具: {name}"
        except Exception as error:
            return f"邮件任务失败: {error}"
