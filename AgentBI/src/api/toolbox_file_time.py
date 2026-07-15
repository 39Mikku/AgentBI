from fastapi import APIRouter, HTTPException, Request, status

from AgentBI.src.schemas.toolbox_file_time_schema import (
    FileTimeJobResponse,
    FileTimePreview,
    FileTimeRequest,
)
from AgentBI.src.services.toolbox.file_time.service import (
    FileTimeService,
    FileTimeValidationError,
)


router = APIRouter(prefix="/toolbox/file-time", tags=["toolbox-file-time"])


def get_file_time_service(request: Request) -> FileTimeService:
    service = getattr(request.app.state, "file_time_service", None)
    if service is None:
        service = FileTimeService()
        request.app.state.file_time_service = service
    return service


@router.post("/preview", response_model=FileTimePreview)
def preview_file_time(request: Request, payload: FileTimeRequest):
    try:
        return get_file_time_service(request).preview(payload)
    except (FileTimeValidationError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/jobs", response_model=FileTimeJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_file_time_job(request: Request, payload: FileTimeRequest):
    try:
        return get_file_time_service(request).start(payload)
    except (FileTimeValidationError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=FileTimeJobResponse)
def get_file_time_job(request: Request, job_id: str):
    job = get_file_time_service(request).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="文件处理任务不存在")
    return job

