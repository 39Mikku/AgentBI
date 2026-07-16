from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from AgentBI.src.schemas.image_generation_schema import GeneratedImage


_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}


class ImageArtifactStore:
    def __init__(self, root: str | Path, public_prefix: str = "/generated-images"):
        self.root = Path(root)
        self.public_prefix = "/" + public_prefix.strip("/")

    @staticmethod
    def _user_folder(user_id: str) -> str:
        return hashlib.sha256(user_id.strip().lower().encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _safe_scope(scope_id: str | None) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", (scope_id or "direct")).strip("-")
        return normalized[:80] or "direct"

    def save(
        self,
        *,
        user_id: str,
        scope_id: str | None,
        image_bytes: bytes,
        media_type: str,
        metadata: dict[str, Any],
    ) -> GeneratedImage:
        extension = _EXTENSIONS.get(media_type)
        if not extension:
            raise ValueError("unsupported image media type")
        image_id = uuid4().hex
        relative = Path(self._user_folder(user_id)) / self._safe_scope(scope_id) / f"{image_id}{extension}"
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(image_bytes)
        relative_path = relative.as_posix()
        return GeneratedImage(
            id=image_id,
            url=f"{self.public_prefix}/{relative_path}",
            relative_path=relative_path,
            media_type=media_type,
            mode=str(metadata.get("mode") or "lite"),
            model=str(metadata.get("model") or ""),
            aspect_ratio=str(metadata.get("aspect_ratio") or "square"),
            width=metadata.get("width"),
            height=metadata.get("height"),
            prompt=str(metadata.get("prompt") or ""),
        )

