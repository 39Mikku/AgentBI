from fastapi import APIRouter, File, Form, HTTPException, Query, Request, Response, UploadFile, status

from AgentBI.src.schemas.studio_asset_schema import StudioAssetResponse


router = APIRouter(prefix="/assets", tags=["studio-assets"])


def _service(request: Request):
    service = getattr(request.app.state, "studio_asset_service", None)
    if not service:
        raise HTTPException(status_code=503, detail="附件服务尚未初始化")
    return service


@router.post("", response_model=StudioAssetResponse, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    request: Request,
    user_id: str = Form(min_length=1),
    file: UploadFile = File(),
):
    try:
        document = _service(request).upload(
            user_id=user_id,
            filename=file.filename or "attachment",
            content_type=file.content_type or "application/octet-stream",
            data=await file.read(),
        )
        return StudioAssetResponse.from_document(document)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("", response_model=list[StudioAssetResponse])
def list_assets(
    request: Request,
    user_id: str = Query(min_length=1),
    kind: str | None = None,
    source: str | None = None,
    search: str | None = None,
):
    repository = _service(request).repository
    return [
        StudioAssetResponse.from_document(item)
        for item in repository.list_assets(user_id, kind=kind, source=source, search=search)
    ]


@router.get("/{asset_id}/content")
def asset_content(asset_id: str, request: Request, user_id: str = Query(min_length=1)):
    service = _service(request)
    asset = service.repository.get_asset(asset_id, user_id)
    if not asset:
        raise HTTPException(status_code=404, detail="附件不存在")
    if asset.get("deleted_at"):
        raise HTTPException(status_code=410, detail="附件已删除")
    try:
        data = service.content_for(asset)
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail="附件文件不存在") from error
    disposition = "inline" if asset["kind"] in {"image", "video"} else "attachment"
    return Response(
        content=data,
        media_type=asset["mime_type"],
        headers={"Content-Disposition": f'{disposition}; filename="{asset["filename"]}"'},
    )


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(asset_id: str, request: Request, user_id: str = Query(min_length=1)):
    try:
        _service(request).delete_asset(asset_id, user_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail="附件不存在") from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
