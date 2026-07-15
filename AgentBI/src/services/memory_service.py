import math
import re
from typing import Any

from AgentBI.src.repositories.sqlite_chat_repository import SqliteChatRepository
from AgentBI.src.services.chat_service import build_context_messages
from AgentBI.src.services.model_task_service import ModelTaskService


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return -1.0
    denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
    return sum(a * b for a, b in zip(left, right)) / denominator if denominator else -1.0


def rank_similar(query: list[float], rows: list[dict[str, Any]], threshold: float, limit: int) -> list[dict[str, Any]]:
    ranked = []
    for row in rows:
        similarity = cosine_similarity(query, row.get("vector", []))
        if similarity >= threshold:
            ranked.append({**row, "similarity": similarity})
    ranked.sort(key=lambda item: item["similarity"], reverse=True)
    return ranked[:limit]


def memory_update_due(new_message_count: int, interval_turns: int) -> bool:
    return new_message_count >= max(2, interval_turns) * 2


def estimate_tokens(messages: list[dict[str, Any]]) -> int:
    text = "\n".join(str(item.get("content", "")) for item in messages)
    ascii_count = sum(1 for char in text if ord(char) < 128)
    return max(1, (ascii_count + 3) // 4 + (len(text) - ascii_count))


def build_context_bundle(
    path: list[dict[str, Any]],
    context_turns: int,
    strategy: str,
    summary: str | None,
    summary_until_message_id: str | None,
    keep_recent_turns: int,
) -> dict[str, Any]:
    messages = [item for item in path if item.get("role") in {"user", "assistant"}]
    if strategy != "compression" or not summary:
        return {"summary": None, "messages": build_context_messages(messages, context_turns)}
    ids = [str(item.get("_id")) for item in messages]
    if str(summary_until_message_id) not in ids:
        return {"summary": None, "messages": build_context_messages(messages, context_turns)}
    start = ids.index(str(summary_until_message_id)) + 1
    recent = messages[start:]
    recent = recent[-max(1, keep_recent_turns) * 2 :]
    return {"summary": summary, "messages": build_context_messages(recent, 0)}


def format_messages(messages: list[dict[str, Any]]) -> str:
    return "\n".join(f"{item.get('role')}: {item.get('content', '')}" for item in messages)


class MemoryService:
    def __init__(self, repository: SqliteChatRepository, model_tasks: ModelTaskService | None = None):
        self.repository = repository
        self.model_tasks = model_tasks or ModelTaskService(repository)

    def core_memory(self, user_id: str, assistant: dict[str, Any]) -> str | None:
        if not assistant.get("memory_enabled"):
            return None
        return self.repository.get_assistant_memory(user_id, assistant["_id"]).get("summary") or None

    def context_bundle(self, thread: dict[str, Any], assistant: dict[str, Any], context_turns: int) -> dict[str, Any]:
        return build_context_bundle(
            self.repository.get_active_path(thread["_id"], thread["user_id"]),
            context_turns,
            assistant.get("context_strategy", "window"),
            thread.get("context_summary"),
            thread.get("context_summary_until_message_id"),
            assistant.get("compression_keep_recent_turns", 4),
        )

    async def ensure_history_index(self, user_id: str, assistant_id: str) -> str | None:
        route = self.repository.get_model_route(user_id, "embedding")
        if not route:
            return None
        model_key = f"{route['provider_id']}:{route['model']}"
        existing = {row["message_id"] for row in self.repository.list_message_embeddings(user_id, assistant_id, model_key)}
        missing = [item for item in self.repository.list_assistant_messages(user_id, assistant_id) if item["_id"] not in existing and item.get("content")]
        for offset in range(0, len(missing), 10):
            batch = missing[offset : offset + 10]
            embedded = await self.model_tasks.embed(user_id, [item["content"] for item in batch])
            if not embedded:
                return None
            returned_key, vectors = embedded
            for message, vector in zip(batch, vectors):
                self.repository.save_message_embedding(message["_id"], user_id, assistant_id, returned_key, vector)
        return model_key

    async def search_history(
        self,
        user_id: str,
        assistant: dict[str, Any],
        query: str,
        exclude_conversation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        model_key = await self.ensure_history_index(user_id, assistant["_id"])
        embedded = await self.model_tasks.embed(user_id, [query]) if model_key else None
        if not embedded:
            return []
        returned_key, vectors = embedded
        rows = self.repository.list_message_embeddings(user_id, assistant["_id"], returned_key)
        if exclude_conversation_id:
            rows = [item for item in rows if item.get("conversation_id") != exclude_conversation_id]
        return rank_similar(
            vectors[0], rows,
            float(assistant.get("history_similarity_threshold", 0.58)),
            int(assistant.get("history_result_limit", 3)),
        )

    async def update_memory_if_due(self, user_id: str, assistant: dict[str, Any], force: bool = False) -> dict[str, Any] | None:
        if not assistant.get("memory_enabled"):
            return None
        memory = self.repository.get_assistant_memory(user_id, assistant["_id"])
        messages = self.repository.list_assistant_messages(user_id, assistant["_id"])
        marker = memory.get("last_summarized_message_id")
        if marker:
            ids = [item["_id"] for item in messages]
            messages = messages[ids.index(marker) + 1 :] if marker in ids else messages
        if not force and not memory_update_due(len(messages), int(assistant.get("memory_update_interval", 12))):
            return None
        if not messages:
            return memory
        summary = await self.model_tasks.complete(
            user_id, "memory",
            "Maintain a concise, durable memory for this user and assistant. Keep stable preferences, goals, decisions and relationships. Remove transient chatter. Return only the updated memory.",
            f"Existing memory:\n{memory.get('summary') or '(empty)'}\n\nNew conversation material:\n{format_messages(messages)}",
        )
        return self.repository.save_assistant_memory(user_id, assistant["_id"], summary, messages[-1]["_id"]) if summary else None

    async def update_context_summary_if_due(self, thread: dict[str, Any], assistant: dict[str, Any]) -> dict[str, Any] | None:
        if assistant.get("context_strategy") != "compression":
            return None
        path = [item for item in self.repository.get_active_path(thread["_id"], thread["user_id"]) if item.get("role") in {"user", "assistant"}]
        turns = len(path) // 2
        if turns < int(assistant.get("compression_threshold_turns", 12)) and estimate_tokens(path) < int(assistant.get("compression_threshold_tokens", 8000)):
            return None
        cutoff = len(path) - max(1, int(assistant.get("compression_keep_recent_turns", 4))) * 2
        if cutoff <= 0:
            return None
        old = path[:cutoff]
        marker = thread.get("context_summary_until_message_id")
        previous_summary = thread.get("context_summary")
        if marker:
            path_ids = [item["_id"] for item in path]
            if marker in path_ids:
                marker_index = path_ids.index(marker)
                old = path[marker_index + 1 : cutoff]
            else:
                previous_summary = None
        if not old:
            return None
        summary = await self.model_tasks.complete(
            thread["user_id"], "compression",
            "Compress earlier conversation context faithfully. Preserve decisions, facts, unresolved tasks and references needed to continue. Return only the summary.",
            f"Previous summary:\n{previous_summary or '(empty)'}\n\nNew older messages:\n{format_messages(old)}",
        )
        return self.repository.save_context_summary(thread["_id"], thread["user_id"], summary, old[-1]["_id"]) if summary else None

    async def generate_title(self, thread: dict[str, Any]) -> str | None:
        if thread.get("title") not in {"未命名会话", "新对话"}:
            return None
        messages = [item for item in self.repository.get_active_path(thread["_id"], thread["user_id"]) if item.get("role") in {"user", "assistant"}][:2]
        if len(messages) < 2:
            return None
        title = await self.model_tasks.complete(
            thread["user_id"], "title",
            "Create a concise conversation title in the user's language. Return only the title, 8 to 18 Chinese characters or equivalent length, without quotes or punctuation at the end.",
            format_messages(messages),
        )
        if not title:
            return None
        title = re.sub(r"^[\s\"'《》]+|[\s\"'。！!？?《》]+$", "", title)[:60]
        updated = self.repository.update_conversation(thread["_id"], thread["user_id"], {"title": title})
        return updated.get("title") if updated else None

    async def maintain_after_reply(self, thread: dict[str, Any], assistant: dict[str, Any]) -> None:
        if assistant.get("history_search_enabled"):
            await self.ensure_history_index(thread["user_id"], assistant["_id"])
        await self.update_memory_if_due(thread["user_id"], assistant)
        latest = self.repository.get_conversation(thread["_id"], thread["user_id"]) or thread
        await self.update_context_summary_if_due(latest, assistant)
