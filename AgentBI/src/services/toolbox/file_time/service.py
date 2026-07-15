from __future__ import annotations

import ctypes
import os
import re
import shutil
import sys
import threading
import uuid
from datetime import datetime, time
from pathlib import Path
from typing import Protocol

from AgentBI.src.schemas.toolbox_file_time_schema import (
    FileTimeJobResponse,
    FileTimePreview,
    FileTimeRequest,
)


class FileTimeValidationError(ValueError):
    pass


class CreationTimeWriter(Protocol):
    def set_creation_time(self, path: Path, timestamp: float) -> None: ...


class WindowsFileTimeWriter:
    _WINDOWS_EPOCH_OFFSET = 11_644_473_600

    def set_creation_time(self, path: Path, timestamp: float) -> None:
        if sys.platform != "win32":
            raise FileTimeValidationError("文件创建时间修改仅支持 Windows")

        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        create_file = kernel32.CreateFileW
        create_file.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        create_file.restype = wintypes.HANDLE
        set_file_time = kernel32.SetFileTime
        set_file_time.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        )
        set_file_time.restype = wintypes.BOOL

        file_write_attributes = 0x0100
        share_all = 0x00000001 | 0x00000002 | 0x00000004
        open_existing = 3
        handle = create_file(str(path), file_write_attributes, share_all, None, open_existing, 0, None)
        if handle == wintypes.HANDLE(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            ticks = int((timestamp + self._WINDOWS_EPOCH_OFFSET) * 10_000_000)
            file_time = wintypes.FILETIME(ticks & 0xFFFFFFFF, ticks >> 32)
            if not set_file_time(handle, ctypes.byref(file_time), None, None):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            kernel32.CloseHandle(handle)


_FILENAME_TIME_PATTERNS = (
    re.compile(r"(?<!\d)(20\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})(?!\d)"),
    re.compile(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(?!\d)"),
)


def extract_filename_time(filename: str) -> datetime | None:
    for pattern in _FILENAME_TIME_PATTERNS:
        match = pattern.search(filename)
        if match is None:
            continue
        try:
            return datetime(*(int(part) for part in match.groups()))
        except ValueError:
            return None
    return None


class FileTimeService:
    def __init__(self, creation_time_writer: CreationTimeWriter | None = None):
        self.creation_time_writer = creation_time_writer or WindowsFileTimeWriter()
        self._jobs: dict[str, FileTimeJobResponse] = {}
        self._lock = threading.RLock()

    def preview(self, payload: FileTimeRequest) -> FileTimePreview:
        input_dir, output_dir = self._validate_directories(payload)
        preview = FileTimePreview(operation=payload.operation)
        start_at, end_at = self._date_bounds(payload)

        for path in self._iter_files(input_dir, output_dir):
            preview.total_files += 1
            relative = path.relative_to(input_dir).as_posix()
            if len(preview.examples) < 20:
                preview.examples.append(relative)
            if payload.operation in {"creation_from_modified", "modified_from_creation"}:
                preview.update_count += 1
            elif payload.operation == "filename_to_creation":
                if extract_filename_time(path.name) is None:
                    preview.move_count += 1
                else:
                    preview.update_count += 1
            elif start_at <= datetime.fromtimestamp(path.stat().st_ctime) <= end_at:
                preview.move_count += 1
            else:
                preview.skip_count += 1
        return preview

    def start(self, payload: FileTimeRequest) -> FileTimeJobResponse:
        self._validate_directories(payload)
        job = FileTimeJobResponse(
            id=uuid.uuid4().hex,
            operation=payload.operation,
            status="queued",
        )
        with self._lock:
            self._jobs[job.id] = job
        thread = threading.Thread(target=self._run_stored_job, args=(job.id, payload), daemon=True)
        thread.start()
        return job.model_copy(deep=True)

    def run_now(self, payload: FileTimeRequest) -> FileTimeJobResponse:
        job = FileTimeJobResponse(
            id=uuid.uuid4().hex,
            operation=payload.operation,
            status="queued",
        )
        self._execute(job, payload)
        return job.model_copy(deep=True)

    def get_job(self, job_id: str) -> FileTimeJobResponse | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.model_copy(deep=True) if job is not None else None

    def _run_stored_job(self, job_id: str, payload: FileTimeRequest) -> None:
        with self._lock:
            job = self._jobs[job_id]
        self._execute(job, payload)

    def _execute(self, job: FileTimeJobResponse, payload: FileTimeRequest) -> None:
        job.status = "running"
        job.started_at = datetime.now().isoformat(timespec="seconds")
        try:
            input_dir, output_dir = self._validate_directories(payload)
            files = list(self._iter_files(input_dir, output_dir))
            job.total_files = len(files)
            start_at, end_at = self._date_bounds(payload)

            for path in files:
                try:
                    self._execute_file(job, payload, input_dir, output_dir, path, start_at, end_at)
                except Exception as exc:
                    job.failed_count += 1
                    if len(job.errors) < 50:
                        job.errors.append(f"{path.relative_to(input_dir).as_posix()}: {exc}")
                finally:
                    job.processed_files += 1
            job.status = "completed"
        except Exception as exc:
            job.status = "failed"
            job.failed_count += 1
            job.errors.append(str(exc))
        finally:
            job.completed_at = datetime.now().isoformat(timespec="seconds")

    def _execute_file(
        self,
        job: FileTimeJobResponse,
        payload: FileTimeRequest,
        input_dir: Path,
        output_dir: Path | None,
        path: Path,
        start_at: datetime,
        end_at: datetime,
    ) -> None:
        stat = path.stat()
        if payload.operation == "creation_from_modified":
            self.creation_time_writer.set_creation_time(path, stat.st_mtime)
            job.updated_count += 1
            return
        if payload.operation == "modified_from_creation":
            os.utime(path, (stat.st_atime, stat.st_ctime))
            job.updated_count += 1
            return
        if payload.operation == "filename_to_creation":
            extracted = extract_filename_time(path.name)
            if extracted is not None:
                self.creation_time_writer.set_creation_time(path, extracted.timestamp())
                job.updated_count += 1
            else:
                self._move_file(input_dir, output_dir, path)
                job.moved_count += 1
            return
        created_at = datetime.fromtimestamp(stat.st_ctime)
        if start_at <= created_at <= end_at:
            self._move_file(input_dir, output_dir, path)
            job.moved_count += 1
        else:
            job.skipped_count += 1

    @staticmethod
    def _move_file(input_dir: Path, output_dir: Path | None, path: Path) -> None:
        if output_dir is None:
            raise FileTimeValidationError("当前操作缺少输出目录")
        target = output_dir / path.relative_to(input_dir)
        if target.exists():
            raise FileExistsError("目标文件已存在")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(target))

    @staticmethod
    def _validate_directories(payload: FileTimeRequest) -> tuple[Path, Path | None]:
        input_dir = Path(payload.input_directory).expanduser().resolve(strict=False)
        if not input_dir.exists() or not input_dir.is_dir():
            raise FileTimeValidationError("输入目录不存在或不是目录")
        output_dir = None
        if payload.output_directory:
            output_dir = Path(payload.output_directory).expanduser().resolve(strict=False)
            if input_dir == output_dir:
                raise FileTimeValidationError("输入目录和输出目录不能相同")
            if output_dir.exists() and not output_dir.is_dir():
                raise FileTimeValidationError("输出路径不是目录")
        return input_dir, output_dir

    @staticmethod
    def _iter_files(input_dir: Path, output_dir: Path | None):
        for root, directories, files in os.walk(input_dir):
            root_path = Path(root)
            directories[:] = [
                name
                for name in directories
                if output_dir is None or (root_path / name).resolve(strict=False) != output_dir
            ]
            for filename in files:
                yield root_path / filename

    @staticmethod
    def _date_bounds(payload: FileTimeRequest) -> tuple[datetime, datetime]:
        if payload.operation != "move_by_creation_range":
            return datetime.min, datetime.max
        if payload.start_date is None or payload.end_date is None:
            raise FileTimeValidationError("按日期移动文件需要开始和结束日期")
        return datetime.combine(payload.start_date, time.min), datetime.combine(payload.end_date, time.max)

