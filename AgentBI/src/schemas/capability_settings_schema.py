from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EmptyCapabilityConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MusicSubagentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    search_result_limit: int = Field(default=3, ge=1, le=10)
    daily_result_limit: int = Field(default=10, ge=1, le=30)


class BilibiliSubagentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_result_limit: int = Field(default=3, ge=1, le=10)
    creator_scan_limit: int = Field(default=20, ge=1, le=50)


class TavilySearchConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_results: int = Field(default=5, ge=1, le=20)
    search_depth: Literal["ultra-fast", "fast", "basic", "advanced"] = "basic"


CAPABILITY_CONFIG_MODELS: dict[str, type[BaseModel]] = {
    "agent.email": EmptyCapabilityConfig,
    "agent.music": MusicSubagentConfig,
    "agent.bilibili": BilibiliSubagentConfig,
    "tool.web_search": TavilySearchConfig,
}

CAPABILITY_CONFIG_FIELDS: dict[str, list[dict[str, Any]]] = {
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
    "tool.web_search": [
        {
            "key": "max_results",
            "label": "搜索结果数",
            "description": "每次网页搜索最多返回的来源数量",
            "type": "number",
            "minimum": 1,
            "maximum": 20,
        },
        {
            "key": "search_depth",
            "label": "搜索深度",
            "description": "速度与相关性的平衡；advanced 会使用更多 Tavily Credits",
            "type": "select",
            "options": [
                {"label": "极速", "value": "ultra-fast"},
                {"label": "快速", "value": "fast"},
                {"label": "标准", "value": "basic"},
                {"label": "深度", "value": "advanced"},
            ],
        },
    ],
}


def resolve_capability_config(capability_id: str, value: dict[str, Any] | None = None) -> dict[str, Any]:
    model = CAPABILITY_CONFIG_MODELS.get(capability_id)
    if model is None:
        raise KeyError(capability_id)
    return model.model_validate(value or {}).model_dump()


class CapabilitySettingsUpdate(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class CapabilitySettingOption(BaseModel):
    label: str
    value: str


class CapabilitySettingField(BaseModel):
    key: str
    label: str
    description: str
    type: Literal["number", "boolean", "text", "select"]
    minimum: int | float | None = None
    maximum: int | float | None = None
    options: list[CapabilitySettingOption] = Field(default_factory=list)


class CapabilitySettingsResponse(BaseModel):
    capability_id: str
    display_name: str
    description: str
    kind: Literal["subagent", "tool"]
    config: dict[str, Any] = Field(default_factory=dict)
    fields: list[CapabilitySettingField] = Field(default_factory=list)
