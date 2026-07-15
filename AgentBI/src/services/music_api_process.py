from __future__ import annotations

import asyncio
import os
import re
import subprocess
import time
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path
from typing import Any

import httpx

from AgentBI.src.logging.logging import Logger

logger = Logger.get_logger(__name__)

HealthProbe = Callable[[str], Awaitable[bool]]
ProcessFactory = Callable[..., Awaitable[Any]]
SyncProcessFactory = Callable[..., Any]


class MusicApiProcessManager:
    """Own the bundled music API process for the lifetime of FastAPI."""

    def __init__(
        self,
        enabled: bool = True,
        port: int = 3300,
        startup_timeout: float = 15,
        command: Sequence[str] | None = None,
        *,
        poll_interval: float = 0.25,
        process_factory: ProcessFactory | None = None,
        sync_process_factory: SyncProcessFactory | None = None,
        health_probe: HealthProbe | None = None,
        working_directory: str | Path | None = None,
    ) -> None:
        self.enabled = enabled
        self.port = port
        self.startup_timeout = startup_timeout
        self.poll_interval = poll_interval
        self.base_url = f"http://127.0.0.1:{port}"
        self.working_directory = Path(working_directory or self._default_working_directory())
        self.command = tuple(command or ("node", str(self.working_directory / "app.cjs")))
        self._process_factory = process_factory
        self._sync_process_factory = sync_process_factory or subprocess.Popen
        self._health_probe = health_probe or self._default_health_probe
        self._process: Any | None = None
        self._log_tasks: list[asyncio.Task[None]] = []
        self._restart_consumed = False
        self._uses_sync_process = False
        self.available = False

    @staticmethod
    def _default_working_directory() -> Path:
        return Path(__file__).resolve().parents[2] / "vendor" / "netease-music-api"

    async def _default_health_probe(self, base_url: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(f"{base_url}/health")
            return response.status_code == 200
        except httpx.HTTPError:
            return False

    async def start(self) -> bool:
        if not self.enabled:
            self.available = False
            return False
        if self._process is not None and self._process.returncode is None:
            self.available = await self._health_probe(self.base_url)
            return self.available

        await self._spawn()
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() <= deadline:
            if self._process.returncode is not None:
                break
            if await self._health_probe(self.base_url):
                self.available = True
                logger.info("网易云音乐内部服务已就绪")
                return True
            await asyncio.sleep(self.poll_interval)

        self.available = False
        await self._stop_process()
        logger.warning("网易云音乐内部服务启动失败，音乐能力暂时不可用")
        return False

    async def ensure_running(self) -> bool:
        if not self.enabled:
            return False
        if self._process is not None and self._process.returncode is None:
            self.available = await self._health_probe(self.base_url)
            return self.available
        if self._restart_consumed:
            self.available = False
            return False

        self._restart_consumed = True
        logger.warning("网易云音乐内部服务意外退出，尝试恢复一次")
        return await self.start()

    async def stop(self) -> None:
        self.available = False
        await self._stop_process()

    async def _spawn(self) -> None:
        kwargs: dict[str, Any] = {
            "cwd": str(self.working_directory),
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
            "env": os.environ.copy(),
        }
        if os.name == "nt":
            kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        if self._process_factory is not None:
            self._uses_sync_process = False
            self._process = await self._process_factory(*self.command, **kwargs)
        else:
            self._uses_sync_process = True
            self._process = await asyncio.to_thread(self._sync_process_factory, self.command, **kwargs)
        self._log_tasks = []
        for stream, level in (
            (getattr(self._process, "stdout", None), "info"),
            (getattr(self._process, "stderr", None), "warning"),
        ):
            if stream is not None:
                self._log_tasks.append(
                    asyncio.create_task(self._forward_logs(stream, level, self._uses_sync_process))
                )

    async def _stop_process(self) -> None:
        process = self._process
        self._process = None
        if process is not None and process.returncode is None:
            process.terminate()
            try:
                await asyncio.wait_for(self._wait_process(process), timeout=3)
            except asyncio.TimeoutError:
                process.kill()
                await self._wait_process(process)
        for task in self._log_tasks:
            task.cancel()
        if self._log_tasks:
            await asyncio.gather(*self._log_tasks, return_exceptions=True)
        self._log_tasks = []
        if process is not None and self._uses_sync_process:
            for stream in (getattr(process, "stdout", None), getattr(process, "stderr", None)):
                if stream is not None and not stream.closed:
                    stream.close()

    async def _wait_process(self, process: Any) -> Any:
        if self._uses_sync_process:
            return await asyncio.to_thread(process.wait)
        return await process.wait()

    async def _forward_logs(self, stream: Any, level: str, sync_stream: bool) -> None:
        log = getattr(logger, level)
        while True:
            line = await asyncio.to_thread(stream.readline) if sync_stream else await stream.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace").strip()
            if not text or "cookie" in text.lower():
                continue
            sanitized = re.sub(r"[\x00-\x1f\x7f]", "", text)[:500]
            if sanitized:
                log("[music-api] %s", sanitized)
