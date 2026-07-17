from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from AgentBI.src.schemas.toolbox_tts_schema import TtsProviderId
from AgentBI.src.services.playground.state_templates import (
    StateTemplateId,
    validate_state_variables,
)


ProfileType = Literal["character", "world"]
PromptSlot = Literal[
    "system_start",
    "system_end",
    "after_last_assistant",
    "before_latest_user",
    "after_latest_user",
]
ThinkingLevel = Literal["off", "low", "medium", "high"]
StateVariableType = Literal["text", "progress", "list"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlaygroundPreferencesUpdate(StrictModel):
    provider_id: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    temperature: float = Field(default=1.0, ge=0, le=2)
    context_turns: int = Field(default=24, ge=0, le=200)
    thinking_level: ThinkingLevel = "medium"
    summary_provider_id: str | None = Field(default=None, max_length=200)
    summary_model: str | None = Field(default=None, max_length=200)
    summary_trigger_messages: int = Field(default=24, ge=4, le=500)
    summary_retain_messages: int = Field(default=8, ge=2, le=100)


class PlaygroundPreferencesResponse(PlaygroundPreferencesUpdate):
    user_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SummaryOverrideSettings(StrictModel):
    enabled: bool = False
    trigger_new_message_count: int | None = Field(default=None, ge=4, le=500)
    retain_recent_message_count: int | None = Field(default=None, ge=2, le=100)
    provider_id: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    injection_position: PromptSlot = "system_end"


class StateVariable(StrictModel):
    key: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_]*$")
    type: StateVariableType
    label: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    initial_value: Any = None
    group: str = Field(default="", max_length=80)
    order: int = Field(default=0, ge=-10000, le=10000)
    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def validate_progress_range(self) -> Self:
        if self.type == "progress":
            if self.minimum is None:
                self.minimum = 0
            if self.maximum is None:
                self.maximum = 100
            if self.minimum >= self.maximum:
                raise ValueError("进度变量 minimum 必须小于 maximum")
        return self


class StatePanelSettings(StrictModel):
    enabled: bool = False
    template: StateTemplateId = "custom"
    variables: list[StateVariable] = Field(default_factory=list, max_length=80)
    update_instructions: str = Field(default="", max_length=6000)
    injection_position: PromptSlot = "system_end"

    @model_validator(mode="after")
    def preserve_template_contract(self) -> Self:
        normalized = validate_state_variables(
            self.template,
            [item.model_dump() for item in self.variables],
        )
        self.variables = [StateVariable.model_validate(item) for item in normalized]
        return self


class ActionOptionsSettings(StrictModel):
    enabled: bool = False
    style_prompt: str = Field(default="", max_length=4000)


class PlaygroundTtsSettings(StrictModel):
    enabled: bool = False
    auto_play: bool = False
    provider: TtsProviderId | None = None
    model: str | None = Field(default=None, max_length=128)
    voice_id: str | None = Field(default=None, max_length=256)
    audio_format: Literal["mp3", "wav", "pcm"] = "mp3"
    parameters: dict[str, Any] = Field(default_factory=dict)


class PlaygroundProfileSettings(StrictModel):
    summary: SummaryOverrideSettings = Field(default_factory=SummaryOverrideSettings)
    state: StatePanelSettings = Field(default_factory=StatePanelSettings)
    action_options: ActionOptionsSettings = Field(default_factory=ActionOptionsSettings)
    tts: PlaygroundTtsSettings = Field(default_factory=PlaygroundTtsSettings)


class PlaygroundProfileCreate(StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    profile_type: ProfileType
    name: str = Field(min_length=1, max_length=100)
    avatar_attachment_id: str | None = Field(default=None, max_length=100)
    background_attachment_id: str | None = Field(default=None, max_length=100)
    main_prompt: str = Field(default="", max_length=30000)
    opening_message: str = Field(default="", max_length=30000)
    settings: PlaygroundProfileSettings = Field(default_factory=PlaygroundProfileSettings)

    @model_validator(mode="after")
    def disable_world_tts(self) -> Self:
        if self.profile_type == "world" and self.settings.tts.enabled:
            raise ValueError("世界模式不支持 TTS")
        return self


class PlaygroundProfileUpdate(StrictModel):
    profile_type: ProfileType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    avatar_attachment_id: str | None = Field(default=None, max_length=100)
    background_attachment_id: str | None = Field(default=None, max_length=100)
    main_prompt: str | None = Field(default=None, max_length=30000)
    opening_message: str | None = Field(default=None, max_length=30000)
    settings: PlaygroundProfileSettings | None = None


class PlaygroundProfileResponse(PlaygroundProfileCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "PlaygroundProfileResponse":
        return cls(id=str(document["_id"]), **{key: value for key, value in document.items() if key != "_id"})


class PromptModuleInput(StrictModel):
    id: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=30000)
    enabled: bool = True
    injection_position: PromptSlot = "system_end"
    sort_order: int = Field(default=0, ge=-10000, le=10000)


class PromptModuleResponse(PromptModuleInput):
    id: str
    profile_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "PromptModuleResponse":
        return cls(id=str(document["_id"]), **{key: value for key, value in document.items() if key != "_id"})


class PromptModuleList(StrictModel):
    items: list[PromptModuleInput] = Field(default_factory=list, max_length=200)


class PersonaUpsert(StrictModel):
    name: str = Field(default="", max_length=100)
    avatar_attachment_id: str | None = Field(default=None, max_length=100)
    identity_text: str = Field(default="", max_length=12000)
    background: str = Field(default="", max_length=12000)
    personality: str = Field(default="", max_length=12000)
    initial_relationship: str = Field(default="", max_length=12000)
    enabled: bool = True
    injection_position: PromptSlot = "system_end"


class PersonaResponse(PersonaUpsert):
    profile_id: str
    user_id: str
    updated_at: datetime


class ContextEntryInput(StrictModel):
    id: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(default="", max_length=100)
    content: str = Field(min_length=1, max_length=30000)
    enabled: bool = True
    activation_mode: Literal["constant", "keyword"] = "constant"
    keywords: list[str] = Field(default_factory=list, max_length=100)
    scan_depth: int = Field(default=8, ge=1, le=200)
    injection_position: PromptSlot = "system_end"
    priority: int = Field(default=0, ge=-10000, le=10000)

    @field_validator("keywords")
    @classmethod
    def normalize_keywords(cls, values: list[str]) -> list[str]:
        result: list[str] = []
        for value in values:
            normalized = value.strip()
            if normalized and normalized not in result:
                result.append(normalized)
        return result

    @model_validator(mode="after")
    def require_keyword_trigger(self) -> Self:
        if self.activation_mode == "keyword" and not self.keywords:
            raise ValueError("关键词触发条目至少需要一个关键词")
        return self


class ContextEntryResponse(ContextEntryInput):
    id: str
    profile_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> "ContextEntryResponse":
        return cls(id=str(document["_id"]), **{key: value for key, value in document.items() if key != "_id"})


class ContextEntryList(StrictModel):
    items: list[ContextEntryInput] = Field(default_factory=list, max_length=1000)


class ConversationSummaryUpdate(StrictModel):
    content: str | None = Field(default=None, max_length=100000)
    status: Literal["idle", "pending", "running", "failed", "stale"] | None = None
    summarized_through_message_id: str | None = Field(default=None, max_length=100)
    last_trigger_message_id: str | None = Field(default=None, max_length=100)
    trigger_new_message_count: int | None = Field(default=None, ge=4, le=500)
    retain_recent_message_count: int | None = Field(default=None, ge=2, le=100)
    provider_id: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    injection_position: PromptSlot | None = None
    last_error: str | None = Field(default=None, max_length=4000)


class ConversationSummaryResponse(StrictModel):
    conversation_id: str
    user_id: str
    content: str = ""
    status: Literal["idle", "pending", "running", "failed", "stale"] = "idle"
    summarized_through_message_id: str | None = None
    last_trigger_message_id: str | None = None
    trigger_new_message_count: int = 24
    retain_recent_message_count: int = 8
    provider_id: str | None = None
    model: str | None = None
    injection_position: PromptSlot = "system_end"
    last_error: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PlaygroundConversationCreate(StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    profile_id: str = Field(min_length=1, max_length=100)
    profile_type: ProfileType
    title: str | None = Field(default=None, max_length=120)


class PlaygroundConversationUpdate(StrictModel):
    title: str = Field(min_length=1, max_length=120)


class PlaygroundConversationBranchCreate(StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    source_message_id: str = Field(min_length=1, max_length=100)
    title: str | None = Field(default=None, min_length=1, max_length=120)


class PlaygroundActiveMessageUpdate(StrictModel):
    user_id: str = Field(min_length=1, max_length=320)


class PlaygroundOpeningMessageUpdate(StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    message_id: str = Field(min_length=1, max_length=100)
    content: str = Field(default="", max_length=30000)


class PlaygroundChatStreamRequest(StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    conversation_id: str = Field(min_length=1, max_length=100)
    profile_id: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=30000)


class PlaygroundRetryStreamRequest(StrictModel):
    user_id: str = Field(min_length=1, max_length=320)
    conversation_id: str = Field(min_length=1, max_length=100)
    profile_id: str = Field(min_length=1, max_length=100)
    message_id: str = Field(min_length=1, max_length=100)


class PlaygroundEditStreamRequest(PlaygroundRetryStreamRequest):
    content: str = Field(min_length=1, max_length=30000)
