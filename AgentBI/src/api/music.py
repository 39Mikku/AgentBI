from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from AgentBI.src.services.netease_music_client import NeteaseMusicClient

router = APIRouter(prefix="/music", tags=["music"])


def get_music_client(request: Request) -> NeteaseMusicClient:
    return NeteaseMusicClient(
        request.app.state.music_api_process,
        cookie=os.getenv("NCM_COOKIE", ""),
        audio_level=os.getenv("NCM_AUDIO_LEVEL", "standard"),
    )


@router.get("/status")
async def music_status(request: Request):
    ready = await request.app.state.music_api_process.ensure_running()
    return {
        "enabled": request.app.state.music_api_process.enabled,
        "ready": ready,
        "cookie_configured": bool(os.getenv("NCM_COOKIE", "").strip()),
    }


@router.get("/tracks/{track_id}/stream")
async def stream_track(track_id: str, request: Request):
    playback = await get_music_client(request).resolve_playback_url(track_id)
    if not playback.available or not playback.url:
        raise HTTPException(status_code=404, detail=playback.unavailable_reason or "歌曲暂不可播放")
    return RedirectResponse(
        playback.url,
        status_code=307,
        headers={"Cache-Control": "no-store"},
    )

