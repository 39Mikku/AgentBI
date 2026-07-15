from fastapi import APIRouter, HTTPException, Request

from AgentBI.src.schemas.toolbox_system_schema import (
    DirectorySelectionRequest,
    DirectorySelectionResponse,
)
from AgentBI.src.services.toolbox.directory_picker import NativeDirectoryPicker


router = APIRouter(prefix="/toolbox/system", tags=["toolbox-system"])


def get_directory_picker(request: Request) -> NativeDirectoryPicker:
    picker = getattr(request.app.state, "directory_picker", None)
    if picker is None:
        picker = NativeDirectoryPicker()
        request.app.state.directory_picker = picker
    return picker


@router.post("/select-directory", response_model=DirectorySelectionResponse)
def select_directory(request: Request, payload: DirectorySelectionRequest):
    try:
        selected = get_directory_picker(request).choose(payload.title, payload.initial_directory)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"无法打开 Windows 目录选择窗口：{exc}") from exc
    return {"path": selected, "cancelled": selected is None}

