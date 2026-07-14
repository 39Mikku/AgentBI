from copy import deepcopy
from typing import Any


DEFAULT_ASSISTANT_PROMPT = "你是 AgentBI 工作台的默认助手。回答应清晰、直接，并根据已挂载能力完成任务。"

CAPABILITIES: dict[str, dict[str, str]] = {
    "agent.email": {
        "id": "agent.email",
        "name": "邮件子代理",
        "kind": "subagent",
        "description": "撰写邮件、查询联系人并发送邮件。",
        "prompt": "需要撰写或发送邮件时，调用 delegate_email 委派给邮件子代理。",
    },
}

DEFAULT_ASSISTANT_CAPABILITIES = list(CAPABILITIES)


def enabled_capabilities(capability_ids: list[str] | None) -> list[dict[str, Any]]:
    return [deepcopy(CAPABILITIES[capability_id]) for capability_id in capability_ids or [] if capability_id in CAPABILITIES]


def capability_prompt(capability_ids: list[str] | None) -> str:
    return "\n".join(capability["prompt"] for capability in enabled_capabilities(capability_ids))
