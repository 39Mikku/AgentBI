from __future__ import annotations

import re
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from AgentBI.src.schemas.toolbox_moegirl_schema import (
    MoegirlArtifactDocumentResponse,
    MoegirlArtifactSummaryResponse,
    MoegirlFetchRequest,
    MoegirlFetchResponse,
    MoegirlRefineRequest,
)
from AgentBI.src.api.dependencies import get_chat_repository
from AgentBI.src.services.model_task_service import (
    ModelTaskConfigurationError,
    ModelTaskEmptyResponseError,
    ModelTaskService,
)
from AgentBI.src.services.toolbox.moegirl.artifact_store import MoegirlArtifactStore
from AgentBI.src.services.toolbox.moegirl.scraper import (
    MoegirlContentError,
    MoegirlNotFoundError,
    MoegirlUpstreamError,
    MoegirlValidationError,
)
from AgentBI.src.services.toolbox.moegirl.service import MoegirlArchiveService
from AgentBI.src.services.toolbox.moegirl.refiner import (
    AI_REFINEMENT_SYSTEM_PROMPT,
    build_ai_refinement_prompt,
    normalize_ai_markdown,
)


router = APIRouter(prefix="/toolbox/moegirl", tags=["toolbox-moegirl"])

UserIdQuery = Annotated[str, Query(min_length=1)]
_UNSAFE_FILENAME_PATTERN = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]+')


def get_moegirl_artifact_store(request: Request) -> MoegirlArtifactStore:
    store = getattr(request.app.state, "moegirl_artifact_store", None)
    if store is None:
        store = MoegirlArtifactStore()
        request.app.state.moegirl_artifact_store = store
    return store


def get_moegirl_archive_service(request: Request) -> MoegirlArchiveService:
    service = getattr(request.app.state, "moegirl_archive_service", None)
    if service is None:
        service = MoegirlArchiveService(store=get_moegirl_artifact_store(request))
        request.app.state.moegirl_archive_service = service
    return service


def get_model_task_service(request: Request) -> ModelTaskService:
    service = getattr(request.app.state, "model_task_service", None)
    if service is None:
        service = ModelTaskService(get_chat_repository(request))
        request.app.state.model_task_service = service
    return service


@router.post("/fetch", response_model=MoegirlFetchResponse)
async def fetch_moegirl_page(request: Request, payload: MoegirlFetchRequest):
    try:
        return await get_moegirl_archive_service(request).fetch(
            payload.user_id,
            payload.name,
        )
    except MoegirlValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except MoegirlNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (MoegirlUpstreamError, MoegirlContentError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="萌娘百科归档写入失败") from exc


@router.get(
    "/artifacts",
    response_model=list[MoegirlArtifactSummaryResponse],
)
def list_moegirl_artifacts(request: Request, user_id: UserIdQuery):
    normalized_user_id = _normalize_user_id(user_id)
    try:
        return get_moegirl_artifact_store(request).list(normalized_user_id)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="萌娘百科归档读取失败") from exc


@router.get(
    "/artifacts/{artifact_id}",
    response_model=MoegirlArtifactDocumentResponse,
)
def get_moegirl_artifact(
    request: Request,
    artifact_id: str,
    user_id: UserIdQuery,
):
    return _require_artifact(request, _normalize_user_id(user_id), artifact_id)


@router.get("/artifacts/{artifact_id}/download")
def download_moegirl_artifact(
    request: Request,
    artifact_id: str,
    user_id: UserIdQuery,
):
    document = _require_artifact(
        request,
        _normalize_user_id(user_id),
        artifact_id,
    )
    utf8_filename = quote(_safe_filename(document.title), safe="")
    disposition = (
        f'attachment; filename="moegirl-{document.id}.md"; '
        f"filename*=UTF-8''{utf8_filename}"
    )
    return Response(
        content=document.markdown.encode("utf-8"),
        headers={
            "Content-Type": "text/markdown; charset=utf-8",
            "Content-Disposition": disposition,
        },
    )


@router.post(
    "/artifacts/{artifact_id}/refine",
    response_model=MoegirlArtifactDocumentResponse,
)
async def refine_moegirl_artifact(
    request: Request,
    artifact_id: str,
    payload: MoegirlRefineRequest,
):
    document = _require_artifact(request, payload.user_id, artifact_id)
    try:
        result = await get_model_task_service(request).complete_with_chat_preferences(
            payload.user_id,
            AI_REFINEMENT_SYSTEM_PROMPT,
            build_ai_refinement_prompt(
                document.title,
                document.source_url,
                document.markdown,
            ),
        )
        markdown = normalize_ai_markdown(result.text)
        if not markdown:
            raise ModelTaskEmptyResponseError("模型未返回可用的 Markdown")
    except ModelTaskConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ModelTaskEmptyResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"AI 精炼失败：{exc}") from exc

    try:
        updated = get_moegirl_artifact_store(request).replace_markdown(
            payload.user_id,
            artifact_id,
            markdown,
        )
    except OSError as exc:
        raise HTTPException(status_code=500, detail="AI 精炼结果写入失败") from exc
    if updated is None:
        raise HTTPException(status_code=404, detail="萌娘百科归档不存在")
    return updated


@router.delete(
    "/artifacts/{artifact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_moegirl_artifact(
    request: Request,
    artifact_id: str,
    user_id: UserIdQuery,
):
    normalized_user_id = _normalize_user_id(user_id)
    try:
        deleted = get_moegirl_artifact_store(request).delete(
            normalized_user_id,
            artifact_id,
        )
    except OSError as exc:
        raise HTTPException(status_code=500, detail="萌娘百科归档删除失败") from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="萌娘百科归档不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _normalize_user_id(user_id: str) -> str:
    normalized = user_id.strip()
    if not normalized or len(normalized) > 320:
        raise HTTPException(
            status_code=422,
            detail="用户标识不能为空且不能超过 320 个字符",
        )
    return normalized


def _require_artifact(request: Request, user_id: str, artifact_id: str):
    try:
        document = get_moegirl_artifact_store(request).get(user_id, artifact_id)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="萌娘百科归档读取失败") from exc
    if document is None:
        raise HTTPException(status_code=404, detail="萌娘百科归档不存在")
    return document


def _safe_filename(title: str) -> str:
    normalized = _UNSAFE_FILENAME_PATTERN.sub("_", title).strip(" .")
    if not normalized:
        normalized = "moegirl"
    return f"{normalized[:120]}.md"
