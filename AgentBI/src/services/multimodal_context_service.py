from __future__ import annotations

import base64
from typing import Any

from AgentBI.src.services.model_task_service import ModelTaskConfigurationError, ModelTaskService


def _match_context_messages(
    context: list[dict[str, Any]], path: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], dict[str, Any] | None]]:
    candidates = [item for item in path if item.get("role") in {"user", "assistant"}]
    cursor = len(candidates) - 1
    matched: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for context_message in reversed(context):
        found = None
        for index in range(cursor, -1, -1):
            candidate = candidates[index]
            if (
                candidate.get("role") == context_message.get("role")
                and candidate.get("content") == context_message.get("content")
            ):
                found = candidate
                cursor = index - 1
                break
        matched.append((context_message, found))
    matched.reverse()
    return matched


class MultimodalContextService:
    def __init__(self, repository: Any, asset_service: Any, model_tasks: ModelTaskService | None = None):
        self.repository = repository
        self.asset_service = asset_service
        self.model_tasks = model_tasks or ModelTaskService(repository)

    async def prepare(
        self,
        *,
        user_id: str,
        provider_id: str,
        model: str,
        context: list[dict[str, Any]],
        path: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        pairs = _match_context_messages(context, path)
        supports_vision = self.repository.model_supports_vision(user_id, provider_id, model)
        assets_by_message: dict[str, list[dict[str, Any]]] = {}
        pending_images: list[dict[str, Any]] = []
        for _, message in pairs:
            if not message or message.get("role") != "user":
                continue
            assets = self.repository.list_message_assets(message["_id"], user_id)
            assets = [item for item in assets if not item.get("deleted_at")]
            assets_by_message[message["_id"]] = assets
            if not supports_vision:
                for asset in assets:
                    if asset["kind"] == "image" and not asset.get("vision_summary"):
                        pending_images.append(asset)
        if pending_images:
            images = [
                {
                    "id": asset["_id"],
                    "filename": asset["filename"],
                    "mime_type": asset["mime_type"],
                    "data": self.asset_service.content_for(asset),
                }
                for asset in pending_images
            ]
            descriptions = await self.model_tasks.describe_images(user_id, images)
            if not descriptions:
                raise ModelTaskConfigurationError("当前聊天模型不支持图片，请先在模型工作台配置识图模型")
            for asset in pending_images:
                summary = descriptions.get(asset["_id"])
                if summary:
                    self.repository.update_asset_derived_text(
                        asset["_id"], user_id, vision_summary=summary
                    )
                    asset["vision_summary"] = summary
        prepared: list[dict[str, Any]] = []
        for context_message, message in pairs:
            result = dict(context_message)
            if not message or message.get("role") != "user":
                prepared.append(result)
                continue
            assets = assets_by_message.get(message["_id"], [])
            text = str(context_message.get("content") or "")
            hidden: list[str] = []
            images: list[dict[str, Any]] = []
            for asset in assets:
                if asset["kind"] == "docx" and asset.get("extracted_text"):
                    hidden.append(
                        f'<document_attachment filename="{asset["filename"]}">\n'
                        f'{asset["extracted_text"]}\n</document_attachment>'
                    )
                elif asset["kind"] == "image":
                    if supports_vision:
                        encoded = base64.b64encode(self.asset_service.content_for(asset)).decode("ascii")
                        images.append(
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{asset['mime_type']};base64,{encoded}"},
                            }
                        )
                    elif asset.get("vision_summary"):
                        hidden.append(
                            f'<image_attachment filename="{asset["filename"]}">\n'
                            f'{asset["vision_summary"]}\n</image_attachment>'
                        )
            combined = "\n\n".join(part for part in (text, *hidden) if part).strip()
            if images:
                result["content"] = [
                    {"type": "text", "text": combined or "请结合所附图片回答。"},
                    *images,
                ]
            else:
                result["content"] = combined
            prepared.append(result)
        return prepared
