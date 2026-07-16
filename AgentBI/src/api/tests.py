from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from AgentBI.src.repositories.sqlite_test_repository import TestRepositoryConflictError
from AgentBI.src.schemas.test_schema import (
    CreateAttemptRequest,
    CreateTestRequest,
    RetryAnalysisRequest,
    SaveAnswersRequest,
    SubmitAttemptRequest,
    TestMode,
    TestPreferencesUpdateRequest,
)
from AgentBI.src.services.test_model_service import (
    TestModelConfigurationError,
    TestModelUpstreamError,
    TestStructuredOutputError,
)
from AgentBI.src.services.test_service import (
    TestConflictError,
    TestNotFoundError,
    TestService,
)


router = APIRouter(tags=["tests"])


def _service(request: Request) -> TestService:
    service = getattr(request.app.state, "test_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Test 服务尚未就绪")
    return service


def _translate(exc: Exception) -> HTTPException:
    if isinstance(exc, TestNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, (TestConflictError, TestRepositoryConflictError, TestModelConfigurationError)):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, (TestModelUpstreamError, TestStructuredOutputError)):
        return HTTPException(status_code=502, detail=str(exc))
    if isinstance(exc, (ValueError, KeyError)):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Test 服务执行失败")


@router.get("/tests/preferences")
def get_preferences(request: Request, user_id: str = Query(min_length=1, max_length=320)):
    try:
        return _service(request).get_or_initialize_preferences(user_id.strip())
    except Exception as exc:
        raise _translate(exc) from exc


@router.put("/tests/preferences")
def update_preferences(request: Request, payload: TestPreferencesUpdateRequest):
    try:
        return _service(request).update_preferences(payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/tests")
async def create_test(request: Request, payload: CreateTestRequest, response: Response):
    try:
        result = await _service(request).create_test(payload)
    except Exception as exc:
        raise _translate(exc) from exc
    if result["state"] == "generating":
        response.status_code = status.HTTP_202_ACCEPTED
    elif result["state"] == "failed":
        raise HTTPException(status_code=409, detail=result.get("error_message") or "测试生成失败，请显式重试")
    elif result.get("created"):
        response.status_code = status.HTTP_201_CREATED
        return result["session"]
    else:
        response.status_code = status.HTTP_200_OK
        return result["session"]
    return result


@router.get("/tests/creation-requests/{request_id}")
def generation_status(
    request: Request,
    request_id: UUID,
    user_id: str = Query(min_length=1, max_length=320),
):
    try:
        return _service(request).get_generation_status(user_id.strip(), str(request_id))
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/tests")
def list_tests(
    request: Request,
    user_id: str = Query(min_length=1, max_length=320),
    mode: TestMode | None = None,
    cursor: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
):
    try:
        return _service(request).list_tests(
            user_id.strip(), mode.value if mode else None, cursor, limit
        )
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/tests/{test_id}")
def get_test(
    request: Request,
    test_id: str,
    user_id: str = Query(min_length=1, max_length=320),
):
    try:
        return _service(request).get_test(test_id, user_id.strip())
    except Exception as exc:
        raise _translate(exc) from exc


@router.delete("/tests/{test_id}", status_code=204)
def delete_test(
    request: Request,
    test_id: str,
    user_id: str = Query(min_length=1, max_length=320),
):
    try:
        _service(request).delete_test(test_id, user_id.strip())
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/tests/{test_id}/attempts")
def create_attempt(request: Request, test_id: str, payload: CreateAttemptRequest):
    try:
        return _service(request).create_or_resume_attempt(test_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.get("/test-attempts/{attempt_id}")
def get_attempt(
    request: Request,
    attempt_id: str,
    user_id: str = Query(min_length=1, max_length=320),
):
    try:
        return _service(request).get_attempt(attempt_id, user_id.strip())
    except Exception as exc:
        raise _translate(exc) from exc


@router.patch("/test-attempts/{attempt_id}/answers")
def save_answers(request: Request, attempt_id: str, payload: SaveAnswersRequest):
    try:
        return _service(request).save_answers(attempt_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc


@router.post("/test-attempts/{attempt_id}/submit")
async def submit_attempt(
    request: Request, attempt_id: str, payload: SubmitAttemptRequest, response: Response
):
    try:
        result = await _service(request).submit_attempt(attempt_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc
    if result.get("status") == "analyzing":
        response.status_code = status.HTTP_202_ACCEPTED
    return result


@router.post("/test-attempts/{attempt_id}/retry-analysis")
async def retry_analysis(
    request: Request, attempt_id: str, payload: RetryAnalysisRequest, response: Response
):
    try:
        result = await _service(request).retry_analysis(attempt_id, payload)
    except Exception as exc:
        raise _translate(exc) from exc
    if result.get("status") == "analyzing":
        response.status_code = status.HTTP_202_ACCEPTED
    return result
