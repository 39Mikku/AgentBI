from __future__ import annotations

import inspect
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, TypeVar

from pydantic import BaseModel

from AgentBI.src.schemas.test_schema import (
    CreateTestRequest,
    FunAnalysis,
    FunAnalysisInput,
    FunQuestionnaire,
    KnowledgeAnalysis,
    KnowledgeAnalysisInput,
    KnowledgeQuestionnaire,
    ModelSnapshot,
    TestMode,
)
from AgentBI.src.services.openai_compatible_client import (
    create_openai_compatible_client,
)
from AgentBI.src.services.test_structured_output import (
    MAX_STRUCTURED_OUTPUT_BYTES,
    StructuredOutputError,
    StructuredOutputTooLargeError,
    parse_structured_object,
    safe_validation_summary,
)


MAX_TOKENS = 16_000
TEMPERATURE = 1.0
T = TypeVar("T", bound=BaseModel)


class TestModelError(RuntimeError):
    """Base class for stable Test model failures."""


class TestModelConfigurationError(TestModelError):
    """The independently selected Test provider or model is unavailable."""


class TestModelUpstreamError(TestModelError):
    """The upstream request failed or returned no usable text."""


class TestStructuredOutputError(TestModelError):
    """The upstream failed to return schema-valid output after one repair."""


@dataclass(frozen=True)
class PreparedTestModelRoute:
    """Resolved private route kept stable across reservation and model I/O."""

    provider: dict[str, Any]
    provider_id: str
    model: str
    snapshot: ModelSnapshot


def _value(container: object, name: str) -> object | None:
    if isinstance(container, Mapping):
        return container.get(name)
    return getattr(container, name, None)


def _response_text(response: object) -> str:
    choices = _value(response, "choices")
    if not isinstance(choices, (list, tuple)) or not choices:
        raise TestModelUpstreamError("模型未返回可用内容")
    message = _value(choices[0], "message")
    content = _value(message, "content") if message is not None else None
    if not isinstance(content, str):
        raise TestModelUpstreamError("模型未返回可用内容")
    if len(content.encode("utf-8")) <= MAX_STRUCTURED_OUTPUT_BYTES and not content.strip():
        raise TestModelUpstreamError("模型未返回可用内容")
    return content


def _data_block(label: str, content: str) -> str:
    """Present model input as a plain, readable section."""

    return f"--- {label} ---\n{content}\n--- END {label} ---"


def _schema_system_prompt(model_type: type[BaseModel], purpose: str) -> str:
    if model_type is KnowledgeQuestionnaire:
        shape = (
            '{"mode":"knowledge","title":"...","description":"...","questions":['
            '{"id":"q1","prompt":"...","options":[{"id":"a","text":"..."}],'
            '"correct_option_id":"a","explanation":"...","knowledge_points":["..."]}]}'
        )
    elif model_type is FunQuestionnaire:
        shape = (
            '{"mode":"fun","title":"...","description":"...","questions":['
            '{"id":"q1","prompt":"...","options":[{"id":"a","text":"..."}]}]}'
        )
    elif model_type is KnowledgeAnalysis:
        shape = (
            '{"title":"...","summary":"...","mastered":[{"heading":"...","body":"..."}],'
            '"weaknesses":[{"heading":"...","body":"..."}],'
            '"recommendations":[{"heading":"...","body":"..."}],'
            '"charts":[{"kind":"radar|bar|donut","title":"...","items":['
            '{"label":"...","value":80,"max_value":100}]}]}'
        )
    else:
        shape = (
            '{"title":"...","summary":"...","sections":[{"heading":"...","body":"..."}],'
            '"charts":[{"kind":"radar|bar|donut","title":"...","items":['
            '{"label":"...","value":80,"max_value":100}]}]}'
        )
    return (
        f"你是一名擅长{purpose}的中文内容设计者。优先保证内容紧扣主题、表达自然、"
        "选项有区分度，题目和分析本身有质量。请返回一个 JSON 对象，不要使用 Markdown "
        f"代码块。字段结构参考：{shape}"
    )


class TestModelService:
    """Non-streaming, tool-free Test generation and analysis model calls."""

    def __init__(
        self,
        test_repository: Any,
        provider_repository: Any,
        *,
        clock: Callable[[], datetime] | None = None,
    ):
        self.test_repository = test_repository
        self.provider_repository = provider_repository
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _resolve(
        self, user_id: str, role: str
    ) -> tuple[dict[str, Any], str, str]:
        preferences = self.test_repository.get_preferences(user_id)
        if not isinstance(preferences, Mapping):
            raise TestModelConfigurationError("请先配置 Test 模型")

        provider_id = preferences.get(f"{role}_provider_id")
        model = preferences.get(f"{role}_model")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise TestModelConfigurationError(f"请先配置 Test {role} 提供商")
        if not isinstance(model, str) or not model.strip():
            raise TestModelConfigurationError(f"请先配置 Test {role} 模型")

        provider = self.provider_repository.get_provider(provider_id)
        if not isinstance(provider, Mapping):
            raise TestModelConfigurationError("所选 Test 提供商不存在")
        provider_dict = dict(provider)
        if not provider_dict.get("api_key") or not provider_dict.get("base_url"):
            raise TestModelConfigurationError("所选 Test 提供商配置不完整")
        return provider_dict, provider_id.strip(), model.strip()

    async def _complete_text(
        self, client: Any, model: str, messages: list[dict[str, str]]
    ) -> str:
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
                stream=False,
            )
            return _response_text(response)
        except TestModelUpstreamError:
            raise
        except Exception:
            raise TestModelUpstreamError("模型调用失败") from None

    @staticmethod
    async def _close_client(client: Any) -> None:
        close = getattr(client, "close", None)
        if not callable(close):
            return
        try:
            closing = close()
            if inspect.isawaitable(closing):
                await closing
        except Exception:
            # Closing must not replace the operation's controlled result/error.
            return

    async def _structured_call(
        self,
        *,
        provider: dict[str, Any],
        model: str,
        system_prompt: str,
        user_prompt: str,
        model_type: type[T],
        validate: Callable[[T], None] | None = None,
    ) -> T:
        try:
            client = create_openai_compatible_client(provider)
        except Exception:
            raise TestModelUpstreamError("模型客户端初始化失败") from None
        try:
            text = await self._complete_text(
                client,
                model,
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            try:
                result = parse_structured_object(text, model_type)
                if validate:
                    validate(result)
                return result
            except (StructuredOutputError, ValueError) as first_error:
                repair_source = (
                    "[omitted: structured output exceeds 256 KiB]"
                    if isinstance(first_error, StructuredOutputTooLargeError)
                    else text
                )
                repair_prompt = (
                    "上一份回答的 JSON 结构无法解析。请保留原有内容、语言风格和判断，"
                    "只修正为上方示例对应的一个 JSON 对象。\n"
                    + _data_block("原始任务", user_prompt)
                    + "\n"
                    + _data_block("模型原回答", repair_source)
                    + "\n"
                    + _data_block("解析提示", safe_validation_summary(first_error))
                )
                repaired_text = await self._complete_text(
                    client,
                    model,
                    [
                        {
                            "role": "system",
                            "content": system_prompt + "\n这是唯一一次结构修复。",
                        },
                        {"role": "user", "content": repair_prompt},
                    ],
                )
                try:
                    repaired = parse_structured_object(repaired_text, model_type)
                    if validate:
                        validate(repaired)
                    return repaired
                except (StructuredOutputError, ValueError):
                    raise TestStructuredOutputError(
                        "模型连续两次未返回符合 Test schema 的 JSON"
                    ) from None
        finally:
            await self._close_client(client)

    def _snapshot(
        self, provider: dict[str, Any], provider_id: str, model: str
    ) -> ModelSnapshot:
        provider_name = provider.get("name")
        if not isinstance(provider_name, str) or not provider_name.strip():
            provider_name = "未命名提供商"
        return ModelSnapshot(
            provider_id=provider_id,
            provider_name=provider_name.strip(),
            model=model,
            temperature=TEMPERATURE,
            captured_at=self._clock(),
        )

    def prepare_analysis_route(self, user_id: str) -> PreparedTestModelRoute:
        provider, provider_id, model = self._resolve(user_id, "analysis")
        return PreparedTestModelRoute(
            provider=provider,
            provider_id=provider_id,
            model=model,
            snapshot=self._snapshot(provider, provider_id, model),
        )

    async def generate_questionnaire(
        self, user_id: str, request: CreateTestRequest
    ) -> tuple[KnowledgeQuestionnaire | FunQuestionnaire, ModelSnapshot]:
        provider, provider_id, model = self._resolve(user_id, "generation")
        model_type: type[KnowledgeQuestionnaire] | type[FunQuestionnaire]
        model_type = (
            KnowledgeQuestionnaire
            if request.mode is TestMode.KNOWLEDGE
            else FunQuestionnaire
        )
        payload = {
            "mode": request.mode.value,
            "topic": request.topic,
            "requirements": request.requirements,
            "question_count": request.question_count,
            "difficulty": request.difficulty.value if request.difficulty else None,
        }
        user_prompt = (
            "请根据下面的主题和要求设计一份单选测试。\n"
            + _data_block(
                "测试需求",
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            )
        )

        def validate_count(questionnaire: KnowledgeQuestionnaire | FunQuestionnaire) -> None:
            if len(questionnaire.questions) != request.question_count:
                raise ValueError("question count does not match the request")

        mode_rules = (
            "知识测试应直接考察用户指定的主题，不要用相邻领域或泛化常识凑题。"
            if request.mode is TestMode.KNOWLEDGE
            else
            "趣味测试没有标准答案，应通过偏好、习惯、反应、审美或情境选择来推断结果，"
            "不要写成知识问答。"
        )
        generation_system = _schema_system_prompt(
            model_type, "a single-choice questionnaire"
        ) + (
            f"\n请生成 {request.question_count} 道题。{mode_rules}标题、说明、问题和选项都应"
            "围绕用户给出的主题与要求。"
        )
        questionnaire = await self._structured_call(
            provider=provider,
            model=model,
            system_prompt=generation_system,
            user_prompt=user_prompt,
            model_type=model_type,
            validate=validate_count,
        )
        return questionnaire, self._snapshot(provider, provider_id, model)

    async def analyze_knowledge(
        self,
        user_id: str,
        payload: KnowledgeAnalysisInput,
        *,
        prepared_route: PreparedTestModelRoute | None = None,
    ) -> tuple[KnowledgeAnalysis, ModelSnapshot]:
        route = prepared_route or self.prepare_analysis_route(user_id)
        user_prompt = (
            "请结合项目已经计算好的分数与逐题作答，分析掌握情况、薄弱点和改进建议。"
            "不要另行编造或重新计算分数。\n"
            + _data_block("知识测试结果", payload.model_dump_json())
        )
        result = await self._structured_call(
            provider=route.provider,
            model=route.model,
            system_prompt=_schema_system_prompt(
                KnowledgeAnalysis, "a knowledge-test learning analysis"
            ),
            user_prompt=user_prompt,
            model_type=KnowledgeAnalysis,
        )
        return result, route.snapshot

    async def analyze_fun(
        self,
        user_id: str,
        payload: FunAnalysisInput,
        *,
        prepared_route: PreparedTestModelRoute | None = None,
    ) -> tuple[FunAnalysis, ModelSnapshot]:
        route = prepared_route or self.prepare_analysis_route(user_id)
        user_prompt = (
            "请根据全部趣味测试题目与用户选择，给出最终结论、具体解释和有意思的观察。"
            "需要图表时使用 radar、bar 或 donut。\n"
            + _data_block("趣味测试结果", payload.model_dump_json())
        )
        result = await self._structured_call(
            provider=route.provider,
            model=route.model,
            system_prompt=_schema_system_prompt(FunAnalysis, "a fun-test result analysis"),
            user_prompt=user_prompt,
            model_type=FunAnalysis,
        )
        return result, route.snapshot
