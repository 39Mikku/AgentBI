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


@dataclass(frozen=True, slots=True)
class DirectToolRegistration:
    capability_id: str
    display_name: str
    description: str
    prompt: str
    tool_name: str
    tool_description: str
    parameters: dict[str, Any]

    def tool_definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.tool_name,
                "description": self.tool_description,
                "parameters": deepcopy(self.parameters),
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
        description="搜索歌曲、获取每日推荐或红心歌曲，并推送可播放卡片。",
        prompt=(
            "用户提供电影主题曲等描述而非具体歌名时，先调用 search_web 确认具体歌名和歌手；"
            "确认后，或用户已经给出具体歌名时，再调用 delegate_music 委派给音乐子代理。"
        ),
        delegate_name="delegate_music",
        delegate_description="将搜索歌曲、每日推荐、红心歌曲或点歌任务委派给音乐子代理。",
        task_label="音乐任务",
        dependency="music_client",
        agent_module="AgentBI.src.agents.music_agent",
        agent_class_name="MusicAgent",
    ),
    SubagentRegistration(
        capability_id="agent.bilibili",
        display_name="Bilibili 视频子代理",
        description="搜索哔哩哔哩公开视频、获取视频详情并推送可播放卡片。",
        prompt="需要搜索、查找或播放哔哩哔哩视频时，调用 delegate_bilibili 委派给视频子代理。",
        delegate_name="delegate_bilibili",
        delegate_description="将哔哩哔哩视频搜索、详情查询或点播任务委派给视频子代理。",
        task_label="哔哩哔哩视频任务",
        dependency="bilibili_client",
        agent_module="AgentBI.src.agents.bilibili_agent",
        agent_class_name="BilibiliAgent",
    ),
)

DIRECT_TOOLS = (
    DirectToolRegistration(
        capability_id="tool.web_search",
        display_name="Tavily 网页搜索",
        description="检索实时网页信息并返回可引用的标题、摘要与来源链接。",
        prompt=(
            "当问题需要当前、外部或无法从已有上下文确认的信息时，可调用 search_web。"
            "回答时应使用搜索结果中的 URL 作为 Markdown 来源链接。"
        ),
        tool_name="search_web",
        tool_description="使用 Tavily 搜索当前网页信息，返回带 URL 的结构化来源；仅在需要外部信息时调用。",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "要搜索的完整问题或关键词"},
                "topic": {
                    "type": "string",
                    "enum": ["general", "news", "finance"],
                    "description": "普通内容、实时新闻或金融内容",
                },
                "time_range": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "可选的发布时间范围",
                },
            },
            "required": ["query"],
        },
    ),
    DirectToolRegistration(
        capability_id="tool.image_generation",
        display_name="图像生成",
        description="根据文本描述生成一张图片并推送到当前会话。",
        prompt=(
            "当用户明确要求创建、绘制或生成图片时调用 generate_image。"
            "先把需求整理成可直接用于生图的完整提示词：明确主体与动作、场景和构图、视觉风格、"
            "镜头与光线、色彩材质以及必须出现或避免的元素；需要精确文字时用引号写出。"
        ),
        tool_name="generate_image",
        tool_description=(
            "Generate exactly one image. Write a complete production-ready prompt preserving the user's intent. "
            "Include subject, action, setting, composition, visual medium, lighting, palette, materials and explicit constraints. "
            "Choose square, landscape or portrait from the requested composition."
        ),
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A complete image-generation prompt planned from the user's request.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["square", "landscape", "portrait"],
                    "description": "The composition best suited to the request.",
                },
            },
            "required": ["prompt", "aspect_ratio"],
        },
    ),
    DirectToolRegistration(
        capability_id="tool.video_generation",
        display_name="视频生成",
        description="使用 Agnes Video v2.0 发起异步文生视频任务，并在当前会话自动更新进度与成片。",
        prompt=(
            "当用户明确要求创建、生成或制作视频时调用 generate_video。"
            "先把用户需求整理为完整、可直接用于文生视频的提示词，明确主体动作、场景、镜头运动、构图、光线、质感和时间变化。"
            "当前能力仅支持文生视频，不要传入图片、负面提示词或其他未开放参数。"
            "用户明确指定画幅或时长时按最接近的合法档位传入；未指定时省略对应参数，使用能力配置默认值。"
        ),
        tool_name="generate_video",
        tool_description=(
            "Start one asynchronous Agnes Video v2.0 text-to-video job. "
            "Write a complete cinematic prompt that preserves the user's intent. "
            "Only provide aspect ratio or duration when the request makes them clear; otherwise use configured defaults."
        ),
        parameters={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "A complete production-ready text-to-video prompt planned from the user's request.",
                },
                "aspect_ratio": {
                    "type": "string",
                    "enum": ["16:9", "9:16", "1:1", "4:3", "3:4"],
                    "description": "Optional output aspect ratio when the user or composition makes it clear.",
                },
                "duration_seconds": {
                    "type": "string",
                    "enum": ["3", "5", "10", "18"],
                    "description": "Optional duration preset in seconds; choose the nearest preset requested by the user.",
                },
            },
            "required": ["prompt"],
        },
    ),
)

_SUBAGENTS_BY_DELEGATE = {registration.delegate_name: registration for registration in SUBAGENTS}
_DIRECT_TOOLS_BY_NAME = {registration.tool_name: registration for registration in DIRECT_TOOLS}
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
CAPABILITIES.update({
    registration.capability_id: {
        "id": registration.capability_id,
        "name": registration.display_name,
        "kind": "tool",
        "description": registration.description,
        "prompt": registration.prompt,
    }
    for registration in DIRECT_TOOLS
})

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


def direct_tool_definitions(capability_ids: list[str] | None) -> list[dict[str, Any]]:
    enabled = set(capability_ids or [])
    return [
        registration.tool_definition()
        for registration in DIRECT_TOOLS
        if registration.capability_id in enabled
    ]


def get_subagent_registration(delegate_name: str) -> SubagentRegistration | None:
    return _SUBAGENTS_BY_DELEGATE.get(delegate_name)


def get_direct_tool_registration(tool_name: str) -> DirectToolRegistration | None:
    return _DIRECT_TOOLS_BY_NAME.get(tool_name)


def create_subagent(
    delegate_name: str,
    *,
    dependencies: dict[str, Any] | None = None,
    repository: Any = None,
    music_client: Any = None,
    bilibili_client: Any = None,
    settings: dict[str, Any] | None = None,
) -> Any | None:
    registration = get_subagent_registration(delegate_name)
    if not registration:
        return None
    dependency_map = {
        "repository": repository,
        "music_client": music_client,
        "bilibili_client": bilibili_client,
        **(dependencies or {}),
    }
    dependency = dependency_map.get(registration.dependency)
    agent_type = getattr(import_module(registration.agent_module), registration.agent_class_name)
    return agent_type(dependency, settings=settings)
