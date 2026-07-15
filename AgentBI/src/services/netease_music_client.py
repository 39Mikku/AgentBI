from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from AgentBI.src.schemas.music_schema import MusicPlayback, MusicTrack
from AgentBI.src.services.music_api_process import MusicApiProcessManager


class MusicApiError(RuntimeError):
    pass


class MusicServiceUnavailable(MusicApiError):
    pass


class MusicAuthenticationError(MusicApiError):
    pass


class NeteaseMusicClient:
    def __init__(
        self,
        process_manager: MusicApiProcessManager,
        *,
        cookie: str = "",
        audio_level: str = "standard",
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10,
    ) -> None:
        self.process_manager = process_manager
        self.cookie = cookie.strip()
        self.audio_level = audio_level
        self.http_client = http_client
        self.timeout = timeout

    async def search_tracks(self, query: str) -> list[MusicTrack]:
        payload = await self._request(
            "/cloudsearch",
            params={"keywords": query.strip(), "limit": 3, "type": 1},
        )
        songs = self._mapping(payload.get("result")).get("songs") or []
        return [self._normalize_track(song) for song in songs[:3] if isinstance(song, Mapping)]

    async def daily_recommendations(self) -> list[MusicTrack]:
        payload = await self._request("/recommend/songs")
        data = self._mapping(payload.get("data"))
        songs = data.get("dailySongs") or payload.get("recommend") or []
        return [self._normalize_track(song) for song in songs[:10] if isinstance(song, Mapping)]

    async def resolve_track(self, track_id: str) -> MusicTrack:
        payload = await self._request("/song/detail", params={"ids": str(track_id)})
        songs = payload.get("songs") or []
        if not songs or not isinstance(songs[0], Mapping):
            raise MusicApiError("没有找到这首歌")
        return self._normalize_track(songs[0])

    async def resolve_playback_url(self, track_id: str) -> MusicPlayback:
        payload = await self._request(
            "/song/url/v1",
            params={"id": str(track_id), "level": self.audio_level},
        )
        items = payload.get("data") or []
        item = items[0] if items and isinstance(items[0], Mapping) else {}
        url = item.get("url")
        if isinstance(url, str) and url:
            return MusicPlayback(track_id=str(track_id), url=url, available=True)
        reason = item.get("message") or item.get("msg") or "当前音质或账号无法播放"
        return MusicPlayback(
            track_id=str(track_id),
            available=False,
            unavailable_reason=str(reason),
        )

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not await self.process_manager.ensure_running():
            raise MusicServiceUnavailable("音乐服务暂时不可用")
        headers = {"Cookie": self.cookie} if self.cookie else {}
        try:
            if self.http_client is not None:
                response = await self.http_client.get(
                    f"{self.process_manager.base_url}{path}",
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.process_manager.base_url}{path}",
                        params=params,
                        headers=headers,
                    )
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise MusicApiError("网易云音乐接口请求失败") from exc
        if not isinstance(payload, dict):
            raise MusicApiError("网易云音乐接口返回了无效数据")
        code = payload.get("code")
        if response.status_code == 301 or code in {301, "301"}:
            raise MusicAuthenticationError("网易云音乐 Cookie 已失效或未登录")
        try:
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MusicApiError("网易云音乐接口请求失败") from exc
        if isinstance(code, int) and code >= 400:
            raise MusicApiError(f"网易云音乐接口拒绝了请求（{code}）")
        return payload

    @staticmethod
    def _mapping(value: Any) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else {}

    @classmethod
    def _normalize_track(cls, song: Mapping[str, Any]) -> MusicTrack:
        artist_items = song.get("ar") or song.get("artists") or []
        artists = [
            str(item.get("name"))
            for item in artist_items
            if isinstance(item, Mapping) and item.get("name")
        ]
        album = cls._mapping(song.get("al") or song.get("album"))
        restriction = song.get("noCopyrightRcmd")
        privilege = cls._mapping(song.get("privilege"))
        available = restriction is None and privilege.get("st", 0) >= 0
        reason = None if available else "版权或账号限制"
        duration = song.get("dt") if song.get("dt") is not None else song.get("duration")
        return MusicTrack(
            id=str(song.get("id", "")),
            name=str(song.get("name") or "未知歌曲"),
            artists=artists,
            album=str(album.get("name") or ""),
            cover_url=album.get("picUrl"),
            duration_ms=int(duration) if isinstance(duration, (int, float)) else None,
            available=available,
            unavailable_reason=reason,
        )
