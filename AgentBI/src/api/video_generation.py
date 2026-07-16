from fastapi import APIRouter, HTTPException, Query, Request

from AgentBI.src.schemas.video_generation_schema import VideoGenerationJobResponse


router = APIRouter(prefix="/video-generation", tags=["video-generation"])


def _service(request: Request):
    service = getattr(request.app.state, "video_generation_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="视频生成服务尚未初始化")
    return service


@router.get("/jobs/{job_id}", response_model=VideoGenerationJobResponse)
def get_video_generation_job(
    job_id: str,
    request: Request,
    user_id: str = Query(min_length=1),
):
    job = _service(request).get_job(job_id, user_id)
    if not job:
        raise HTTPException(status_code=404, detail="视频生成任务不存在")
    return VideoGenerationJobResponse.from_document(job)
