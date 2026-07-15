from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol

from AgentBI.src.schemas.toolbox_auto_input_schema import AutoInputCreate, AutoInputJobResponse
from AgentBI.src.services.toolbox.auto_input.win32_sender import Win32UnicodeSender


class CharacterSender(Protocol):
    def send_character(self, character: str) -> None: ...


class AutoInputBusyError(RuntimeError):
    pass


@dataclass
class AutoInputJob:
    text: str
    delay_seconds: float
    countdown_seconds: int
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = "countdown"
    countdown_remaining: int = 0
    total_characters: int = 0
    typed_characters: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        self.text = self.text.replace("\r\n", "\n").replace("\r", "\n")
        self.total_characters = len(self.text)
        self.countdown_remaining = self.countdown_seconds

    def response(self) -> AutoInputJobResponse:
        return AutoInputJobResponse(
            id=self.id,
            status=self.status,
            delay_seconds=self.delay_seconds,
            countdown_seconds=self.countdown_seconds,
            countdown_remaining=self.countdown_remaining,
            total_characters=self.total_characters,
            typed_characters=self.typed_characters,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error=self.error,
        )


class AutoInputRunner:
    def __init__(
        self,
        sender: CharacterSender | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.sender = sender or Win32UnicodeSender()
        self.sleep = sleep

    def ensure_supported(self) -> None:
        checker = getattr(self.sender, "ensure_supported", None)
        if checker is not None:
            checker()

    def run(self, job: AutoInputJob, cancel_event: threading.Event) -> None:
        try:
            job.status = "countdown"
            for remaining in range(job.countdown_seconds, 0, -1):
                job.countdown_remaining = remaining
                if cancel_event.is_set():
                    job.status = "cancelled"
                    return
                self.sleep(1)
                if cancel_event.is_set():
                    job.status = "cancelled"
                    return

            job.countdown_remaining = 0
            job.status = "running"
            job.started_at = datetime.now().isoformat(timespec="seconds")
            for index, character in enumerate(job.text):
                if cancel_event.is_set():
                    job.status = "cancelled"
                    return
                self.sender.send_character(character)
                job.typed_characters = index + 1
                if cancel_event.is_set():
                    job.status = "cancelled"
                    return
                if job.delay_seconds and index + 1 < job.total_characters:
                    self.sleep(job.delay_seconds)
            job.status = "completed"
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
        finally:
            if job.status in {"completed", "cancelled", "failed"}:
                job.completed_at = datetime.now().isoformat(timespec="seconds")


class AutoInputService:
    _ACTIVE_STATUSES = {"countdown", "running"}

    def __init__(self, runner: AutoInputRunner | None = None):
        self.runner = runner or AutoInputRunner()
        self._jobs: dict[str, AutoInputJob] = {}
        self._cancel_events: dict[str, threading.Event] = {}
        self._active_job_id: str | None = None
        self._lock = threading.RLock()

    def start(self, payload: AutoInputCreate) -> AutoInputJobResponse:
        checker = getattr(self.runner, "ensure_supported", None)
        if checker is not None:
            checker()
        with self._lock:
            active = self._jobs.get(self._active_job_id or "")
            if active is not None and active.status in self._ACTIVE_STATUSES:
                raise AutoInputBusyError("已有自动输入任务正在运行")
            job = AutoInputJob(
                text=payload.text,
                delay_seconds=payload.delay_seconds,
                countdown_seconds=payload.countdown_seconds,
            )
            cancel_event = threading.Event()
            self._jobs[job.id] = job
            self._cancel_events[job.id] = cancel_event
            self._active_job_id = job.id
        threading.Thread(target=self._run_job, args=(job.id,), daemon=True).start()
        return job.response()

    def get(self, job_id: str) -> AutoInputJobResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.response() if job is not None else None

    def get_active(self) -> AutoInputJobResponse | None:
        with self._lock:
            job = self._jobs.get(self._active_job_id or "")
            if job is None or job.status not in self._ACTIVE_STATUSES:
                return None
            return job.response()

    def cancel(self, job_id: str) -> AutoInputJobResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            event = self._cancel_events.get(job_id)
            if job is None or event is None:
                return None
            event.set()
            return job.response()

    def _run_job(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            cancel_event = self._cancel_events[job_id]
        try:
            self.runner.run(job, cancel_event)
        finally:
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None

