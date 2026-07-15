from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EmptySubagentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MusicSubagentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search_result_limit: int = Field(default=3, ge=1, le=10)
    daily_result_limit: int = Field(default=10, ge=1, le=30)


class BilibiliSubagentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_result_limit: int = Field(default=3, ge=1, le=10)
    creator_scan_limit: int = Field(default=20, ge=1, le=50)


SUBAGENT_CONFIG_MODELS: dict[str, type[BaseModel]] = {
    "agent.email": EmptySubagentConfig,
    "agent.music": MusicSubagentConfig,
    "agent.bilibili": BilibiliSubagentConfig,
}

SUBAGENT_CONFIG_FIELDS: dict[str, list[dict[str, Any]]] = {
    "agent.email": [],
    "agent.music": [
        {
            "key": "search_result_limit",
            "label": "搜索结果数",
            "description": "按歌曲、歌手或关键词搜索时返回的候选数量",
            "type": "number",
            "minimum": 1,
            "maximum": 10,
        },
        {
            "key": "daily_result_limit",
            "label": "每日推荐数",
            "description": "每日推荐卡片最多展示的歌曲数量",
            "type": "number",
            "minimum": 1,
            "maximum": 30,
        },
    ],
    "agent.bilibili": [
        {
            "key": "default_result_limit",
            "label": "视频结果数",
            "description": "全站搜索或 UP 主稿件搜索最终展示的候选数量",
            "type": "number",
            "minimum": 1,
            "maximum": 10,
        },
        {
            "key": "creator_scan_limit",
            "label": "UP 主稿件扫描数",
            "description": "从指定 UP 主的最近稿件中取多少条作为本地筛选候选",
            "type": "number",
            "minimum": 1,
            "maximum": 50,
        },
    ],
}


def resolve_subagent_config(capability_id: str, value: dict[str, Any] | None = None) -> dict[str, Any]:
    model = SUBAGENT_CONFIG_MODELS.get(capability_id)
    if model is None:
        raise KeyError(capability_id)
    return model.model_validate(value or {}).model_dump()


class SubagentSettingsUpdate(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class SubagentSettingField(BaseModel):
    key: str
    label: str
    description: str
    type: Literal["number", "boolean", "text"]
    minimum: int | float | None = None
    maximum: int | float | None = None


class SubagentSettingsResponse(BaseModel):
    capability_id: str
    display_name: str
    description: str
    config: dict[str, Any] = Field(default_factory=dict)
    fields: list[SubagentSettingField] = Field(default_factory=list)
