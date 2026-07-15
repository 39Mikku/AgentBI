from __future__ import annotations

import os
from copy import deepcopy
from typing import Any

from AgentBI.src.services.toolbox.tts.base import TtsProviderAdapter, TtsValidationError


MINIMAX_VOICES = [
    {"id": "male-qn-qingse", "name": "青涩青年"},
    {"id": "male-qn-jingying", "name": "精英青年"},
    {"id": "male-qn-badao", "name": "霸道青年"},
    {"id": "male-qn-daxuesheng", "name": "青年大学生"},
    {"id": "female-shaonv", "name": "少女"},
    {"id": "female-yujie", "name": "御姐"},
    {"id": "female-chengshu", "name": "成熟女性"},
    {"id": "female-tianmei", "name": "甜美女性"},
]

MIMO_VOICES = [
    {"id": "mimo_default", "name": "MiMo 默认"},
    {"id": "冰糖", "name": "冰糖"},
    {"id": "茉莉", "name": "茉莉"},
    {"id": "苏打", "name": "苏打"},
    {"id": "白桦", "name": "白桦"},
    {"id": "Mia", "name": "Mia"},
    {"id": "Chloe", "name": "Chloe"},
    {"id": "Milo", "name": "Milo"},
    {"id": "Dean", "name": "Dean"},
]

VOLCENGINE_VOICES = [
    {"id": "zh_female_vv_uranus_bigtts", "name": "Vivi 2.0"},
    {"id": "zh_male_dayi_saturn_bigtts", "name": "大壹"},
    {"id": "zh_female_meilinvyou_saturn_bigtts", "name": "魅力女友"},
    {"id": "zh_female_santongyongns_saturn_bigtts", "name": "流畅女声"},
    {"id": "zh_male_ruyayichen_saturn_bigtts", "name": "儒雅逸辰"},
]


def _number_field(
    key: str,
    label: str,
    minimum: float,
    maximum: float,
    step: float,
    default: float,
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "type": "number",
        "minimum": minimum,
        "maximum": maximum,
        "step": step,
        "default": default,
    }


PROVIDER_DEFINITIONS: dict[str, dict[str, Any]] = {
    "minimax": {
        "label": "MiniMax",
        "required_env": ["MINIMAX_API_KEY"],
        "models": [
            {"id": "speech-2.8-hd", "label": "Speech 2.8 HD", "voice_kinds": ["builtin", "cloned"]},
            {"id": "speech-2.8-turbo", "label": "Speech 2.8 Turbo", "voice_kinds": ["builtin", "cloned"]},
        ],
        "builtin_voices": MINIMAX_VOICES,
        "audio_formats": ["mp3", "wav", "pcm"],
        "parameters": [
            _number_field("speed", "语速", 0.5, 2.0, 0.1, 1.0),
            _number_field("volume", "音量", 0.1, 10.0, 0.1, 1.0),
            _number_field("pitch", "音调", -12, 12, 1, 0),
            {
                "key": "emotion",
                "label": "情绪",
                "type": "select",
                "default": "",
                "options": [
                    {"label": "自动", "value": ""},
                    {"label": "开心", "value": "happy"},
                    {"label": "悲伤", "value": "sad"},
                    {"label": "愤怒", "value": "angry"},
                    {"label": "平静", "value": "calm"},
                    {"label": "低语", "value": "whisper"},
                ],
            },
        ],
    },
    "bailian": {
        "label": "阿里云百炼",
        "required_env": ["DASHSCOPE_API_KEY", "DASHSCOPE_WORKSPACE_ID"],
        "models": [
            {"id": "cosyvoice-v3.5-plus", "label": "CosyVoice 3.5 Plus", "voice_kinds": ["cloned"]},
            {"id": "cosyvoice-v3.5-flash", "label": "CosyVoice 3.5 Flash", "voice_kinds": ["cloned"]},
        ],
        "builtin_voices": [],
        "audio_formats": ["mp3", "wav", "pcm"],
        "parameters": [
            _number_field("speech_rate", "语速", 0.5, 2.0, 0.1, 1.0),
            _number_field("volume", "音量", 0, 100, 1, 50),
            _number_field("pitch", "音调", 0.5, 2.0, 0.05, 1.0),
            {"key": "instruction", "label": "风格指令", "type": "text", "default": ""},
        ],
    },
    "mimo": {
        "label": "小米 MiMo",
        "required_env": ["MIMO_API_KEY"],
        "models": [
            {"id": "mimo-v2.5-tts", "label": "MiMo V2.5 TTS", "voice_kinds": ["builtin"]},
        ],
        "builtin_voices": MIMO_VOICES,
        "audio_formats": ["mp3", "wav", "pcm"],
        "parameters": [
            {"key": "style", "label": "风格指令", "type": "text", "default": ""},
        ],
    },
    "volcengine": {
        "label": "火山引擎",
        "required_env": ["VOLCENGINE_TTS_APP_ID", "VOLCENGINE_TTS_ACCESS_TOKEN"],
        "models": [
            {"id": "doubao-seed-tts-2.0", "label": "Doubao-Seed-TTS 2.0", "voice_kinds": ["builtin"]},
            {"id": "doubao-seed-icl-2.0", "label": "Doubao-Seed-ICL 2.0", "voice_kinds": ["cloned"]},
        ],
        "builtin_voices": VOLCENGINE_VOICES,
        "audio_formats": ["mp3", "wav", "pcm"],
        "parameters": [
            _number_field("speed_ratio", "语速", 0.5, 2.0, 0.1, 1.0),
            _number_field("volume_ratio", "音量", 0.1, 3.0, 0.1, 1.0),
            {"key": "context_text", "label": "上下文提示", "type": "text", "default": ""},
        ],
    },
}


class TtsProviderRegistry:
    def __init__(self, environment: dict[str, str] | None = None) -> None:
        self.environment = environment if environment is not None else dict(os.environ)
        self._adapters: dict[str, TtsProviderAdapter] = {}

    @classmethod
    def from_environment(cls) -> "TtsProviderRegistry":
        return cls(dict(os.environ))

    def capabilities(self) -> list[dict[str, Any]]:
        capabilities: list[dict[str, Any]] = []
        for provider_id, definition in PROVIDER_DEFINITIONS.items():
            item = deepcopy(definition)
            required = item.pop("required_env")
            missing = [name for name in required if not self.environment.get(name, "").strip()]
            item.update(
                {
                    "id": provider_id,
                    "configured": not missing,
                    "missing_configuration": missing,
                }
            )
            capabilities.append(item)
        return capabilities

    def register(self, adapter: TtsProviderAdapter) -> None:
        self._adapters[adapter.provider_id] = adapter

    def get(self, provider_id: str) -> TtsProviderAdapter:
        if provider_id not in PROVIDER_DEFINITIONS:
            raise TtsValidationError("不支持的语音供应商")
        if provider_id not in self._adapters:
            self._adapters[provider_id] = self._create_adapter(provider_id)
        return self._adapters[provider_id]

    def _create_adapter(self, provider_id: str) -> TtsProviderAdapter:
        if provider_id == "minimax":
            from AgentBI.src.services.toolbox.tts.minimax import MiniMaxTtsAdapter

            return MiniMaxTtsAdapter(api_key=self.environment.get("MINIMAX_API_KEY", ""))
        if provider_id == "bailian":
            from AgentBI.src.services.toolbox.tts.bailian_cosyvoice import BailianCosyVoiceAdapter

            return BailianCosyVoiceAdapter(
                api_key=self.environment.get("DASHSCOPE_API_KEY", ""),
                workspace_id=self.environment.get("DASHSCOPE_WORKSPACE_ID", ""),
            )
        if provider_id == "mimo":
            from AgentBI.src.services.toolbox.tts.mimo import MimoTtsAdapter

            return MimoTtsAdapter(api_key=self.environment.get("MIMO_API_KEY", ""))
        from AgentBI.src.services.toolbox.tts.volcengine import VolcengineTtsAdapter

        return VolcengineTtsAdapter(
            app_id=self.environment.get("VOLCENGINE_TTS_APP_ID", ""),
            access_token=self.environment.get("VOLCENGINE_TTS_ACCESS_TOKEN", ""),
            tts_resource_id=self.environment.get("VOLCENGINE_TTS_RESOURCE_ID", "seed-tts-2.0"),
            icl_resource_id=self.environment.get("VOLCENGINE_ICL_RESOURCE_ID", "seed-icl-2.0"),
        )
