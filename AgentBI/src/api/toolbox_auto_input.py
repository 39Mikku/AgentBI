from fastapi import APIRouter, HTTPException, Request, Response, status

from AgentBI.src.schemas.toolbox_auto_input_schema import AutoInputCreate, AutoInputJobResponse
from AgentBI.src.services.toolbox.auto_input.service import AutoInputBusyError, AutoInputService
from AgentBI.src.services.toolbox.auto_input.win32_sender import UnsupportedDesktopError


router = APIRouter(prefix="/toolbox/auto-input", tags=["toolbox-auto-input"])


def get_auto_input_service(request: Request) -> AutoInputService:
    service = getattr(request.app.state, "auto_input_service", None)
    if service is None:
        service = AutoInputService()
        request.app.state.auto_input_service = service
    return service


@router.post("/jobs", response_model=AutoInputJobResponse, status_code=status.HTTP_202_ACCEPTED)
def create_auto_input_job(request: Request, payload: AutoInputCreate):
    try:
        return get_auto_input_service(request).start(payload)
    except AutoInputBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UnsupportedDesktopError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/jobs/active")
def get_active_auto_input_job(request: Request):
    job = get_auto_input_service(request).get_active()
    if job is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return job


@router.get("/jobs/{job_id}", response_model=AutoInputJobResponse)
def get_auto_input_job(request: Request, job_id: str):
    job = get_auto_input_service(request).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="自动输入任务不存在")
    return job


@router.post("/jobs/{job_id}/cancel", response_model=AutoInputJobResponse)
def cancel_auto_input_job(request: Request, job_id: str):
    job = get_auto_input_service(request).cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="自动输入任务不存在")
    return job

