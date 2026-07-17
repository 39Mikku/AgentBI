from __future__ import annotations

from typing import Any

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.repositories.sqlite_playground_repository import SqlitePlaygroundRepository
from AgentBI.src.services.openai_compatible_client import create_openai_compatible_client


SUMMARY_SYSTEM_PROMPT = """更新一份用于继续长篇角色扮演的精炼记录。只输出 Markdown，固定使用以下栏目：
## 关键事件时间线
## 人物记录
## 人物关系
## 关键物品
## 承诺、秘密与约定
按时间保留会改变剧情、关系或人物认知的事件；合并重复事实；以后续明确事实修正旧信息；
不要记录普通闲聊、短暂动作、当前场景面板或未被文本支持的推测。"""


def _visible_messages(path: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in path
        if item.get("role") in {"user", "assistant"}
        and item.get("status", "complete") == "complete"
    ]


def count_messages_after_trigger(
    path: list[dict[str, Any]],
    summary: dict[str, Any],
) -> int:
    visible = _visible_messages(path)
    ids = [str(item.get("_id") or item.get("id") or "") for item in visible]
    marker = str(summary.get("last_trigger_message_id") or "")
    return len(visible) if marker not in ids else len(visible) - ids.index(marker) - 1


def summary_is_stale(
    path: list[dict[str, Any]],
    summary: dict[str, Any],
) -> bool:
    marker = summary.get("summarized_through_message_id")
    ids = {str(item.get("_id") or item.get("id") or "") for item in _visible_messages(path)}
    return bool(marker) and str(marker) not in ids


class PlaygroundSummarizer:
    def __init__(
        self,
        chat_repository: SqliteChatRepository,
        playground_repository: SqlitePlaygroundRepository,
    ):
        self.chat_repository = chat_repository
        self.playground_repository = playground_repository

    async def ensure_current(
        self,
        thread: dict[str, Any],
        profile: dict[str, Any],
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        summary = self.playground_repository.get_summary(thread["_id"], thread["user_id"])
        path = self.chat_repository.get_active_path(thread["_id"], thread["user_id"])
        if not self._enabled(profile) or not summary_is_stale(path, summary):
            return summary
        return await self._maintain(thread, profile, preferences, force=True, stale=True)

    async def maintain_after_reply(
        self,
        thread: dict[str, Any],
        profile: dict[str, Any],
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        if not self._enabled(profile):
            return self.playground_repository.get_summary(thread["_id"], thread["user_id"])
        return await self._maintain(
            thread, profile, preferences, force=False, stale=False, acquired=False
        )

    def begin_after_reply(
        self,
        thread: dict[str, Any],
        profile: dict[str, Any],
        preferences: dict[str, Any],
    ) -> bool:
        """Atomically mark a due summary as running before a task is scheduled."""

        if not self._enabled(profile):
            return False
        path = self.chat_repository.get_active_path(thread["_id"], thread["user_id"])
        visible = _visible_messages(path)
        current = self.playground_repository.get_summary(thread["_id"], thread["user_id"])
        config = self._configuration(profile, preferences)
        if len(visible) <= config["retain"]:
            return False
        if count_messages_after_trigger(visible, current) < config["trigger"]:
            return False
        return self.playground_repository.try_mark_summary_running(
            thread["_id"],
            thread["user_id"],
            {
                "trigger_new_message_count": config["trigger"],
                "retain_recent_message_count": config["retain"],
                "provider_id": config["provider_id"],
                "model": config["model"],
                "injection_position": config["injection_position"],
            },
        ) is not None

    async def maintain_acquired_after_reply(
        self,
        thread: dict[str, Any],
        profile: dict[str, Any],
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        return await self._maintain(
            thread, profile, preferences, force=True, stale=False, acquired=True
        )

    async def refresh(
        self,
        thread: dict[str, Any],
        profile: dict[str, Any],
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        current = self.playground_repository.get_summary(thread["_id"], thread["user_id"])
        path = self.chat_repository.get_active_path(thread["_id"], thread["user_id"])
        return await self._maintain(
            thread,
            profile,
            preferences,
            force=True,
            stale=summary_is_stale(path, current),
            acquired=False,
        )

    async def _maintain(
        self,
        thread: dict[str, Any],
        profile: dict[str, Any],
        preferences: dict[str, Any],
        *,
        force: bool,
        stale: bool,
        acquired: bool = False,
    ) -> dict[str, Any]:
        conversation_id = thread["_id"]
        user_id = thread["user_id"]
        path = self.chat_repository.get_active_path(conversation_id, user_id)
        visible = _visible_messages(path)
        current = self.playground_repository.get_summary(conversation_id, user_id)
        config = self._configuration(profile, preferences)
        if not force and count_messages_after_trigger(visible, current) < config["trigger"]:
            return current
        if len(visible) <= config["retain"]:
            return current

        if not acquired:
            running = self.playground_repository.try_mark_summary_running(
                conversation_id,
                user_id,
                {
                    "trigger_new_message_count": config["trigger"],
                    "retain_recent_message_count": config["retain"],
                    "provider_id": config["provider_id"],
                    "model": config["model"],
                    "injection_position": config["injection_position"],
                },
            )
            if running is None:
                return self.playground_repository.get_summary(conversation_id, user_id)

        boundary_index = len(visible) - config["retain"] - 1
        boundary_id = str(visible[boundary_index].get("_id") or visible[boundary_index].get("id"))
        leaf_id = str(visible[-1].get("_id") or visible[-1].get("id"))
        try:
            text = await self._generate(
                user_id=user_id,
                provider_id=config["provider_id"],
                model=config["model"],
                previous_summary="" if stale else str(current.get("content") or ""),
                visible=visible,
                previous_boundary=None if stale else current.get("summarized_through_message_id"),
                boundary_index=boundary_index,
            )
        except Exception as error:
            return self.playground_repository.save_summary(
                conversation_id,
                user_id,
                {
                    "status": "failed",
                    "last_error": str(error)[:4000],
                },
            )

        return self.playground_repository.save_summary(
            conversation_id,
            user_id,
            {
                "content": text,
                "status": "idle",
                "summarized_through_message_id": boundary_id,
                "last_trigger_message_id": leaf_id,
                "trigger_new_message_count": config["trigger"],
                "retain_recent_message_count": config["retain"],
                "provider_id": config["provider_id"],
                "model": config["model"],
                "injection_position": config["injection_position"],
                "last_error": None,
            },
        )

    async def _generate(
        self,
        *,
        user_id: str,
        provider_id: str | None,
        model: str | None,
        previous_summary: str,
        visible: list[dict[str, Any]],
        previous_boundary: str | None,
        boundary_index: int,
    ) -> str:
        provider = self.chat_repository.get_provider(provider_id)
        if provider is None:
            raise RuntimeError("Playground 大总结提供商未配置")
        selected_model = model or provider.get("default_model")
        if not selected_model:
            raise RuntimeError("Playground 大总结模型未配置")

        start_index = 0
        if previous_summary and previous_boundary:
            ids = [str(item.get("_id") or item.get("id") or "") for item in visible]
            if str(previous_boundary) in ids:
                start_index = ids.index(str(previous_boundary)) + 1
        source = visible[start_index : boundary_index + 1]
        dialogue = "\n".join(
            f"{('用户' if item['role'] == 'user' else '角色')}：{item.get('content', '')}"
            for item in source
        )
        prompt_parts = []
        if previous_summary:
            prompt_parts.append("现有精炼记录：\n" + previous_summary)
        prompt_parts.append("需要吸收的新对话：\n" + dialogue)
        response = await create_openai_compatible_client(provider).chat.completions.create(
            model=selected_model,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": "\n\n".join(prompt_parts)},
            ],
            temperature=1.0,
        )
        content = response.choices[0].message.content if response.choices else None
        result = content.strip() if content else ""
        if not result:
            raise RuntimeError("大总结模型未返回内容")
        return result

    @staticmethod
    def _enabled(profile: dict[str, Any]) -> bool:
        return bool((((profile.get("settings") or {}).get("summary") or {}).get("enabled")))

    @staticmethod
    def _configuration(
        profile: dict[str, Any],
        preferences: dict[str, Any],
    ) -> dict[str, Any]:
        settings = ((profile.get("settings") or {}).get("summary") or {})
        return {
            "trigger": int(
                settings.get("trigger_new_message_count")
                or preferences.get("summary_trigger_messages")
                or 24
            ),
            "retain": int(
                settings.get("retain_recent_message_count")
                or preferences.get("summary_retain_messages")
                or 8
            ),
            "provider_id": settings.get("provider_id")
            or preferences.get("summary_provider_id")
            or preferences.get("provider_id"),
            "model": settings.get("model")
            or preferences.get("summary_model")
            or preferences.get("model"),
            "injection_position": settings.get("injection_position") or "system_end",
        }
