from __future__ import annotations

import asyncio
import html
import json
import os
import re
import subprocess
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

import httpx

from AgentBI.src.schemas.bilibili_schema import BilibiliVideo

SearchProvider = Callable[[str], Awaitable[dict[str, Any]]]
DetailProvider = Callable[[str], Awaitable[dict[str, Any]]]
CliRunner = Callable[[list[str], dict[str, str]], Awaitable[tuple[int, str, str]]]

_BVID_PATTERN = re.compile(r"^BV[0-9A-Za-z]{10}$")
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
_API_BASE_URL = "https://api.bilibili.com"
_PUBLIC_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
    "Accept": "application/json, text/plain, */*",
}


class BilibiliClientError(RuntimeError):
    pass


class BilibiliClient:
    def __init__(
        self,
        *,
        search_provider: SearchProvider | None = None,
        detail_provider: DetailProvider | None = None,
        cli_runner: CliRunner | None = None,
        cli_command: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 25,
    ) -> None:
        self.http_client = http_client
        self.timeout = timeout
        self.cli_runner = cli_runner or self._run_cli
        self.cli_command = (cli_command or os.getenv("BILI_CLI_COMMAND") or "bili").strip()
        self.detail_provider = detail_provider or self._get_public_video
        self.search_provider = search_provider or self._search_cli_videos

    async def search_videos(self, query: str, limit: int = 3) -> list[BilibiliVideo]:
        keyword = query.strip()
        if not keyword:
            raise BilibiliClientError("请提供视频搜索关键词")
        try:
            payload = await self.search_provider(keyword)
        except BilibiliClientError:
            raise
        except Exception as exc:
            raise BilibiliClientError("哔哩哔哩视频搜索失败") from exc

        items = payload.get("result", []) if isinstance(payload, Mapping) else []
        videos: list[BilibiliVideo] = []
        safe_limit = min(max(int(limit), 1), 10)
        for item in items:
            if not isinstance(item, Mapping) or not self.is_bvid(item.get("bvid")):
                continue
            videos.append(self._normalize_search_video(item))
            if len(videos) >= safe_limit:
                break
        return videos

    async def search_creator_videos(
        self,
        creator: str,
        query: str = "",
        *,
        limit: int = 3,
        scan_limit: int = 20,
    ) -> list[BilibiliVideo]:
        normalized_creator = creator.strip()
        if not normalized_creator:
            raise BilibiliClientError("请提供 UP 主名称或 UID")
        safe_limit = min(max(int(limit), 1), 10)
        safe_scan_limit = min(max(int(scan_limit), safe_limit), 50)
        exact_author_only = False
        try:
            payload = await self._search_cli_creator_videos(normalized_creator, safe_scan_limit)
        except BilibiliClientError:
            if normalized_creator.isdigit():
                raise
            payload = await self.search_provider(" ".join(filter(None, (normalized_creator, query.strip()))))
            exact_author_only = True
        except Exception as exc:
            raise BilibiliClientError("UP 主稿件搜索失败") from exc

        keyword = query.strip().casefold()
        items = payload.get("result", []) if isinstance(payload, Mapping) else []
        videos: list[BilibiliVideo] = []
        for item in items:
            if not isinstance(item, Mapping) or not self.is_bvid(item.get("bvid")):
                continue
            owner = item.get("owner") if isinstance(item.get("owner"), Mapping) else {}
            author = str(item.get("author") or item.get("uname") or owner.get("name") or "").strip()
            if exact_author_only and author.casefold() != normalized_creator.casefold():
                continue
            haystack = "\n".join(
                str(item.get(key) or "")
                for key in ("title", "description", "desc")
            ).casefold()
            if keyword and keyword not in haystack:
                continue
            videos.append(self._normalize_search_video(item))
            if len(videos) >= safe_limit:
                break
        return videos

    async def get_video(self, bvid: str) -> BilibiliVideo:
        normalized_bvid = bvid.strip()
        if not self.is_bvid(normalized_bvid):
            raise BilibiliClientError("无效的 BV 号")
        try:
            payload = await self.detail_provider(normalized_bvid)
        except BilibiliClientError:
            raise
        except Exception as exc:
            raise BilibiliClientError("哔哩哔哩视频详情获取失败") from exc
        if not isinstance(payload, Mapping):
            raise BilibiliClientError("哔哩哔哩返回了无效的视频详情")
        return self._normalize_detail_video(payload, normalized_bvid)

    async def _search_cli_videos(self, keyword: str) -> dict[str, Any]:
        environment = {
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "OUTPUT": "json",
        }
        arguments = [
            self.cli_command,
            "search",
            keyword,
            "--type",
            "video",
            "--max",
            "10",
            "--json",
        ]
        try:
            returncode, stdout, _stderr = await self.cli_runner(arguments, environment)
            payload = json.loads(stdout or "{}")
        except BilibiliClientError:
            raise
        except Exception as exc:
            raise BilibiliClientError("Bilibili CLI 调用失败") from exc
        if returncode != 0 or not isinstance(payload, Mapping) or payload.get("ok") is not True:
            raise BilibiliClientError("Bilibili CLI 搜索失败")
        items = payload.get("data")
        if not isinstance(items, list):
            raise BilibiliClientError("Bilibili CLI 返回了无效搜索数据")

        return {"result": await self._enrich_cli_items(items)}

    async def _search_cli_creator_videos(self, creator: str, scan_limit: int) -> dict[str, Any]:
        environment = {
            **os.environ,
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "OUTPUT": "json",
        }
        arguments = [
            self.cli_command,
            "user-videos",
            creator,
            "--max",
            str(scan_limit),
            "--json",
        ]
        try:
            returncode, stdout, _stderr = await self.cli_runner(arguments, environment)
            payload = json.loads(stdout or "{}")
        except BilibiliClientError:
            raise
        except Exception as exc:
            raise BilibiliClientError("Bilibili CLI 调用失败") from exc
        if returncode != 0 or not isinstance(payload, Mapping) or payload.get("ok") is not True:
            raise BilibiliClientError("Bilibili CLI UP 主稿件搜索失败")
        items = payload.get("data")
        if not isinstance(items, list):
            raise BilibiliClientError("Bilibili CLI 返回了无效稿件数据")
        return {"result": await self._enrich_cli_items(items)}

    async def _enrich_cli_items(self, items: list[Any]) -> list[dict[str, Any]]:
        details = await asyncio.gather(
            *[
                self.detail_provider(str(item.get("bvid")))
                for item in items
                if isinstance(item, Mapping) and self.is_bvid(item.get("bvid"))
            ],
            return_exceptions=True,
        )
        enriched: list[dict[str, Any]] = []
        detail_index = 0
        for item in items:
            if not isinstance(item, Mapping) or not self.is_bvid(item.get("bvid")):
                continue
            merged = dict(item)
            detail = details[detail_index]
            detail_index += 1
            if isinstance(detail, Mapping):
                merged.update(detail)
            enriched.append(merged)
        return enriched

    async def _run_cli(
        self,
        arguments: list[str],
        environment: dict[str, str],
    ) -> tuple[int, str, str]:
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                arguments,
                capture_output=True,
                env=environment,
                creationflags=creationflags,
                timeout=self.timeout,
                check=False,
            )
        except OSError as exc:
            raise BilibiliClientError("未找到 Bilibili CLI，请先安装 bilibili-cli") from exc
        except subprocess.TimeoutExpired as exc:
            raise BilibiliClientError("Bilibili CLI 搜索超时") from exc
        return (
            completed.returncode,
            completed.stdout.decode("utf-8", errors="replace"),
            completed.stderr.decode("utf-8", errors="replace"),
        )

    async def _get_public_video(self, bvid: str) -> dict[str, Any]:
        data = await self._request("/x/web-interface/view", params={"bvid": bvid})
        return data if isinstance(data, dict) else {}

    async def _request(self, path: str, *, params: dict[str, Any]) -> Any:
        try:
            if self.http_client is not None:
                response = await self.http_client.get(
                    f"{_API_BASE_URL}{path}",
                    params=params,
                    headers=_PUBLIC_HEADERS,
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient(
                    headers=_PUBLIC_HEADERS,
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    response = await client.get(f"{_API_BASE_URL}{path}", params=params)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise BilibiliClientError("哔哩哔哩公开接口请求失败") from exc
        if not isinstance(payload, Mapping):
            raise BilibiliClientError("哔哩哔哩返回了无效数据")
        if payload.get("code") not in {0, None}:
            raise BilibiliClientError(f"哔哩哔哩拒绝了请求（{payload.get('code')}）")
        return payload.get("data", payload)

    @staticmethod
    def is_bvid(value: Any) -> bool:
        return isinstance(value, str) and bool(_BVID_PATTERN.fullmatch(value.strip()))

    @classmethod
    def _normalize_search_video(cls, item: Mapping[str, Any]) -> BilibiliVideo:
        bvid = str(item["bvid"]).strip()
        return BilibiliVideo(
            bvid=bvid,
            title=cls._plain_text(item.get("title")) or "未命名视频",
            author=str(item.get("author") or item.get("uname") or ""),
            cover_url=cls._cover_url(item.get("pic")),
            duration_seconds=cls._duration_seconds(item.get("duration")),
            play_count=cls._non_negative_int(item.get("play")),
            published_at=cls._optional_int(item.get("pubdate")),
            description=str(item.get("description") or item.get("desc") or ""),
            url=f"https://www.bilibili.com/video/{bvid}",
        )

    @classmethod
    def _normalize_detail_video(cls, item: Mapping[str, Any], fallback_bvid: str) -> BilibiliVideo:
        bvid = str(item.get("bvid") or fallback_bvid).strip()
        owner = item.get("owner") if isinstance(item.get("owner"), Mapping) else {}
        stat = item.get("stat") if isinstance(item.get("stat"), Mapping) else {}
        return BilibiliVideo(
            bvid=bvid,
            title=cls._plain_text(item.get("title")) or "未命名视频",
            author=str(owner.get("name") or item.get("author") or ""),
            cover_url=cls._cover_url(item.get("pic")),
            duration_seconds=cls._duration_seconds(item.get("duration")),
            play_count=cls._non_negative_int(stat.get("view", item.get("play"))),
            published_at=cls._optional_int(item.get("pubdate")),
            description=str(item.get("desc") or item.get("description") or ""),
            url=f"https://www.bilibili.com/video/{bvid}",
        )

    @staticmethod
    def _plain_text(value: Any) -> str:
        return html.unescape(_HTML_TAG_PATTERN.sub("", str(value or ""))).strip()

    @staticmethod
    def _cover_url(value: Any) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        url = value.strip()
        if url.startswith("//"):
            return f"https:{url}"
        if url.startswith("http://"):
            return f"https://{url.removeprefix('http://')}"
        return url

    @staticmethod
    def _duration_seconds(value: Any) -> int:
        if isinstance(value, (int, float)):
            return max(int(value), 0)
        if not isinstance(value, str):
            return 0
        try:
            parts = [int(part) for part in value.split(":")]
        except ValueError:
            return 0
        if not parts or len(parts) > 3:
            return 0
        total = 0
        for part in parts:
            total = total * 60 + part
        return max(total, 0)

    @staticmethod
    def _optional_int(value: Any) -> int | None:
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    @classmethod
    def _non_negative_int(cls, value: Any) -> int:
        parsed = cls._optional_int(value)
        return max(parsed or 0, 0)
