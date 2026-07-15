from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from importlib import import_module
from typing import Any

DEFAULT_ASSISTANT_PROMPT = "你是 AgentBI 工作台的默认助手。回答应清晰、直接，并根据已挂载能力完成任务。"


@dataclass(frozen=True, slots=True)
class SubagentRegistration:
    capability_id: str
    display_name: str
    description: str
    prompt: str
    delegate_name: str
    delegate_description: str
    task_label: str
    dependency: str
    agent_module: str
    agent_class_name: str

    def tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.delegate_name,
                "description": self.delegate_description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "instruction": {"type": "string", "description": f"完整的{self.task_label}说明"}
                    },
                    "required": ["instruction"],
                },
            },
        }


SUBAGENTS = (
    SubagentRegistration(
        capability_id="agent.email",
        display_name="邮件子代理",
        description="撰写邮件、查询联系人并发送邮件。",
        prompt="需要撰写或发送邮件时，调用 delegate_email 委派给邮件子代理。",
        delegate_name="delegate_email",
        delegate_description="将邮件撰写、收件人查询和发送委派给邮件子代理。",
        task_label="邮件任务",
        dependency="repository",
        agent_module="AgentBI.src.agents.email_agent",
        agent_class_name="EmailAgent",
    ),
    SubagentRegistration(
        capability_id="agent.music",
        display_name="音乐子代理",
        description="搜索歌曲、获取每日推荐并推送可播放卡片。",
        prompt="需要搜索歌曲、每日推荐或点歌时，调用 delegate_music 委派给音乐子代理。",
        delegate_name="delegate_music",
        delegate_description="将搜索歌曲、每日推荐或点歌任务委派给音乐子代理。",
        task_label="音乐任务",
        dependency="music_client",
        agent_module="AgentBI.src.agents.music_agent",
        agent_class_name="MusicAgent",
    ),
)

_SUBAGENTS_BY_DELEGATE = {registration.delegate_name: registration for registration in SUBAGENTS}
CAPABILITIES: dict[str, dict[str, str]] = {
    registration.capability_id: {
        "id": registration.capability_id,
        "name": registration.display_name,
        "kind": "subagent",
        "description": registration.description,
        "prompt": registration.prompt,
    }
    for registration in SUBAGENTS
}

DEFAULT_ASSISTANT_CAPABILITIES = list(CAPABILITIES)


def enabled_capabilities(capability_ids: list[str] | None) -> list[dict[str, Any]]:
    return [
        deepcopy(CAPABILITIES[capability_id])
        for capability_id in capability_ids or []
        if capability_id in CAPABILITIES
    ]


def capability_prompt(capability_ids: list[str] | None) -> str:
    return "\n".join(capability["prompt"] for capability in enabled_capabilities(capability_ids))


def delegation_tool_definitions(capability_ids: list[str] | None) -> list[dict[str, Any]]:
    enabled = set(capability_ids or [])
    return [
        registration.tool_definition()
        for registration in SUBAGENTS
        if registration.capability_id in enabled
    ]


def get_subagent_registration(delegate_name: str) -> SubagentRegistration | None:
    return _SUBAGENTS_BY_DELEGATE.get(delegate_name)


def create_subagent(
    delegate_name: str,
    *,
    repository: Any = None,
    music_client: Any = None,
) -> Any | None:
    registration = get_subagent_registration(delegate_name)
    if not registration:
        return None
    dependency = repository if registration.dependency == "repository" else music_client
    agent_type = getattr(import_module(registration.agent_module), registration.agent_class_name)
    return agent_type(dependency)
