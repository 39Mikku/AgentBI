# Toolbox File Time and Auto Type Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two Windows-local Toolbox utilities for batch file timestamp operations and cancellable Unicode automatic typing.

**Architecture:** FastAPI exposes focused `/toolbox/file-time`, `/toolbox/auto-input`, and `/toolbox/system` routes backed by in-memory job services. File creation times and Unicode keyboard events use Python `ctypes` Win32 bindings, while Vue provides two industrial workbench pages with polling, preview, confirmation, progress, and cancellation.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, ctypes/Win32, Vue 3, TypeScript, Vitest, unittest.

## Global Constraints

- Do not reuse the legacy scripts or their virtual environments.
- Do not add `pywin32` or `pynput`; use Python standard-library Win32 bindings.
- Do not persist tasks, input text, paths, or reports to SQLite.
- Do not implement the legacy per-file manual timestamp workflow.
- Folder selection must use the native Windows directory dialog and still allow manual path editing.
- Automatic tests must never send real keyboard input or mutate user files.
- Do not commit, stage, merge, or push; the user handles Git manually.

---

### Task 1: File-time schemas and planning service

**Files:**
- Create: `AgentBI/src/schemas/toolbox_file_time_schema.py`
- Create: `AgentBI/src/services/toolbox/file_time/service.py`
- Create: `AgentBI/src/services/toolbox/file_time/__init__.py`
- Test: `AgentBI/tests/test_toolbox_file_time_service.py`

**Interfaces:**
- Produces: `FileTimeOperation`, `FileTimeRequest`, `FileTimePreview`, `FileTimeJobResponse`.
- Produces: `extract_filename_time(name: str) -> datetime | None`.
- Produces: `FileTimeService.preview(payload) -> FileTimePreview` and `start(payload) -> FileTimeJobResponse`.

- [ ] **Step 1: Write failing parsing and validation tests**

```python
def test_extracts_all_supported_filename_formats(self):
    expected = datetime(2026, 7, 15, 9, 8, 7)
    for name in (
        "IMG_2026-07-15-09-08-07.jpg",
        "IMG_20260715_090807.jpg",
        "IMG_20260715-090807.jpg",
        "IMG_20260715090807.jpg",
    ):
        self.assertEqual(extract_filename_time(name), expected)

def test_output_is_required_only_for_move_operations(self):
    FileTimeRequest(operation="creation_from_modified", input_directory=self.input)
    with self.assertRaises(ValidationError):
        FileTimeRequest(operation="filename_to_creation", input_directory=self.input)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_file_time_service -v`

Expected: import failure because the schema and service do not exist.

- [ ] **Step 3: Implement strict request models and filename parsing**

```python
FileTimeOperation = Literal[
    "creation_from_modified",
    "modified_from_creation",
    "filename_to_creation",
    "move_by_creation_range",
]

class FileTimeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: FileTimeOperation
    input_directory: str = Field(min_length=1, max_length=4096)
    output_directory: str | None = Field(default=None, max_length=4096)
    start_date: date | None = None
    end_date: date | None = None
```

Implement four anchored search patterns with `datetime(...)` validation and return `None` for impossible dates.

- [ ] **Step 4: Write failing preview tests**

```python
def test_preview_excludes_nested_output_and_preserves_relative_paths(self):
    preview = self.service.preview(self.filename_payload)
    self.assertEqual(preview.total_files, 2)
    self.assertEqual(preview.update_count, 1)
    self.assertEqual(preview.move_count, 1)
    self.assertNotIn("output/already-moved.txt", preview.examples)
```

- [ ] **Step 5: Implement normalized path validation and read-only preview**

Use `Path.resolve(strict=False)` and `os.path.commonpath` to exclude a nested output subtree. Preview must not create the output directory and must return totals plus at most 20 relative example paths.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_file_time_service -v`

Expected: all file-time parsing and preview tests pass.

---

### Task 2: Win32 timestamp mutation and background jobs

**Files:**
- Modify: `AgentBI/src/services/toolbox/file_time/service.py`
- Test: `AgentBI/tests/test_toolbox_file_time_service.py`

**Interfaces:**
- Consumes: validated `FileTimeRequest` from Task 1.
- Produces: `WindowsFileTimeWriter.set_creation_time(path, timestamp)` and an injectable writer protocol.
- Produces: job states `queued`, `running`, `completed`, `failed` with counters and per-file errors.

- [ ] **Step 1: Write failing execution tests using a fake timestamp writer**

```python
def test_filename_mode_updates_matches_and_moves_non_matches(self):
    job = self.service.run_now(self.filename_payload)
    self.assertEqual(job.updated_count, 1)
    self.assertEqual(job.moved_count, 1)
    self.assertTrue((self.output / "nested" / "plain.txt").exists())

def test_existing_target_is_reported_and_never_overwritten(self):
    job = self.service.run_now(self.move_payload)
    self.assertEqual(job.failed_count, 1)
    self.assertEqual((self.output / "same.txt").read_text(), "existing")
```

- [ ] **Step 2: Run tests and verify RED**

Expected: failure because mutation and job execution are not implemented.

- [ ] **Step 3: Implement Win32 creation-time writer**

Use `CreateFileW` with `FILE_WRITE_ATTRIBUTES`, `FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE`, `OPEN_EXISTING`, then convert Unix seconds to Windows 100-nanosecond ticks:

```python
windows_ticks = int((timestamp + 11644473600) * 10_000_000)
filetime = wintypes.FILETIME(windows_ticks & 0xFFFFFFFF, windows_ticks >> 32)
```

Call `SetFileTime(handle, byref(filetime), None, None)` and always `CloseHandle`.

- [ ] **Step 4: Implement all four operations**

- `creation_from_modified`: writer receives `path.stat().st_mtime`.
- `modified_from_creation`: `os.utime(path, (stat.st_atime, stat.st_ctime))`.
- `filename_to_creation`: update recognized files; move unrecognized files without overwrite.
- `move_by_creation_range`: compare local `datetime.fromtimestamp(stat.st_ctime)` against inclusive start/end bounds and move matching files.

- [ ] **Step 5: Add thread-safe background start/status behavior**

`start()` creates a UUID job, stores it under a lock, and runs the same tested executor in a daemon thread. Return copies from `get_job(job_id)` so API serialization cannot mutate internal state.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_file_time_service -v`

Expected: all tests pass using only temporary directories.

---

### Task 3: Native directory selection and file-time API

**Files:**
- Create: `AgentBI/src/schemas/toolbox_system_schema.py`
- Create: `AgentBI/src/services/toolbox/directory_picker.py`
- Create: `AgentBI/src/api/toolbox_system.py`
- Create: `AgentBI/src/api/toolbox_file_time.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_toolbox_file_time_api.py`

**Interfaces:**
- Produces: `POST /toolbox/system/select-directory`.
- Produces: `POST /toolbox/file-time/preview`, `POST /toolbox/file-time/jobs`, `GET /toolbox/file-time/jobs/{job_id}`.

- [ ] **Step 1: Write failing API tests with injected picker and service**

```python
def test_select_directory_returns_selected_path(self):
    response = self.client.post("/toolbox/system/select-directory", json={"title": "选择输入目录"})
    self.assertEqual(response.json(), {"path": "C:\\Media", "cancelled": False})

def test_file_time_preview_and_job_contract(self):
    preview = self.client.post("/toolbox/file-time/preview", json=self.payload)
    self.assertEqual(preview.status_code, 200)
    created = self.client.post("/toolbox/file-time/jobs", json=self.payload)
    self.assertEqual(created.status_code, 202)
```

- [ ] **Step 2: Run tests and verify RED**

Expected: 404 for all new routes.

- [ ] **Step 3: Implement serialized native picker**

Create and destroy a hidden `tkinter.Tk` instance inside a process-wide lock, set it topmost, call `filedialog.askdirectory`, and return cancellation without treating it as an error.

- [ ] **Step 4: Implement API dependency getters and error mapping**

Use `request.app.state.directory_picker` and `request.app.state.file_time_service`, with lazy defaults for tests. Map invalid path/date configuration to HTTP 422 and missing jobs to HTTP 404.

- [ ] **Step 5: Register services and routers in `main.py`**

Instantiate both services after environment loading and include both routers. No database dependency is introduced.

- [ ] **Step 6: Run API and full backend tests**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_file_time_api -v`

Run: `.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"`

Expected: all tests pass.

---

### Task 4: Automatic-input runner and concurrency service

**Files:**
- Create: `AgentBI/src/schemas/toolbox_auto_input_schema.py`
- Create: `AgentBI/src/services/toolbox/auto_input/service.py`
- Create: `AgentBI/src/services/toolbox/auto_input/win32_sender.py`
- Create: `AgentBI/src/services/toolbox/auto_input/__init__.py`
- Test: `AgentBI/tests/test_toolbox_auto_input_service.py`

**Interfaces:**
- Produces: `AutoInputCreate(text, delay_seconds, countdown_seconds)`.
- Produces: `AutoInputRunner.run(job, cancel_event)` with injected sender and sleeper.
- Produces: `AutoInputService.start`, `get`, `get_active`, and `cancel`.

- [ ] **Step 1: Write failing runner tests with a fake sender and no-op sleeper**

```python
def test_runner_normalizes_newlines_and_reports_progress(self):
    job = AutoInputJob(text="你\r\n好", delay_seconds=0, countdown_seconds=1)
    self.runner.run(job, Event())
    self.assertEqual(self.sender.characters, ["你", "\n", "好"])
    self.assertEqual(job.typed_characters, 3)
    self.assertEqual(job.status, "completed")

def test_runner_stops_on_cancel(self):
    cancel = Event()
    self.sender.after_send = cancel.set
    self.runner.run(AutoInputJob(text="abc", delay_seconds=0, countdown_seconds=1), cancel)
    self.assertEqual(self.sender.characters, ["a"])
```

- [ ] **Step 2: Run tests and verify RED**

Expected: import failure because the automatic-input service does not exist.

- [ ] **Step 3: Implement strict schemas, runner, and cancellation**

Normalize CRLF/CR to LF before calculating `total_characters`. Countdown sleeps in one-second units and checks cancellation before and after each sleep. Typing updates the job after every successful character.

- [ ] **Step 4: Write and run a failing single-active-job test**

```python
def test_only_one_job_can_be_active(self):
    self.service.start(self.payload)
    with self.assertRaises(AutoInputBusyError):
        self.service.start(self.payload)
```

- [ ] **Step 5: Implement thread-safe job service**

The service keeps all jobs and the active job ID under a lock. Terminal jobs clear the active ID in `finally`; cancellation sets the matching event and returns the latest job snapshot.

- [ ] **Step 6: Implement Win32 Unicode sender**

Use `SendInput` and `KEYEVENTF_UNICODE`; encode each Python character as UTF-16LE code units so non-BMP characters work. Convert LF to virtual-key Enter down/up events. Raise a clear unsupported-platform error when `sys.platform != "win32"`.

- [ ] **Step 7: Run focused tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_auto_input_service -v`

Expected: all tests pass without sending real input.

---

### Task 5: Automatic-input API

**Files:**
- Create: `AgentBI/src/api/toolbox_auto_input.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_toolbox_auto_input_api.py`

**Interfaces:**
- Produces: `POST /toolbox/auto-input/jobs`.
- Produces: `GET /toolbox/auto-input/jobs/active` and `GET /toolbox/auto-input/jobs/{job_id}`.
- Produces: `POST /toolbox/auto-input/jobs/{job_id}/cancel`.

- [ ] **Step 1: Write failing API contract tests**

```python
def test_start_status_active_and_cancel_contract(self):
    created = self.client.post("/toolbox/auto-input/jobs", json={
        "text": "hello", "delay_seconds": 0.05, "countdown_seconds": 5,
    })
    self.assertEqual(created.status_code, 202)
    job_id = created.json()["id"]
    self.assertEqual(self.client.get("/toolbox/auto-input/jobs/active").status_code, 200)
    self.assertEqual(self.client.post(f"/toolbox/auto-input/jobs/{job_id}/cancel").status_code, 200)
```

- [ ] **Step 2: Run tests and verify RED**

Expected: 404 for new routes.

- [ ] **Step 3: Implement API and main registration**

Map busy jobs to HTTP 409, invalid parameters to 422, unsupported desktop sessions to 503, and missing jobs to 404. Return 204 from the active endpoint when there is no active task.

- [ ] **Step 4: Run focused and full backend tests**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_auto_input_api -v`

Run: `.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"`

Expected: all tests pass.

---

### Task 6: Frontend API clients and pure state helpers

**Files:**
- Create: `Agent-vue/src/api/toolbox-system-types.ts`
- Create: `Agent-vue/src/api/toolbox-system.ts`
- Create: `Agent-vue/src/toolbox/file-time.ts`
- Create: `Agent-vue/src/toolbox/file-time.test.ts`
- Create: `Agent-vue/src/toolbox/auto-input.ts`
- Create: `Agent-vue/src/toolbox/auto-input.test.ts`

**Interfaces:**
- Produces typed functions for directory selection, preview/start/status, automatic-input start/status/cancel.
- Produces `requiresOutput(operation)`, `requiresDateRange(operation)`, `fileTimeProgress(job)`, and `autoInputProgress(job)`.

- [ ] **Step 1: Write failing frontend helper tests**

```typescript
it('requires output only for moving operations', () => {
  expect(requiresOutput('filename_to_creation')).toBe(true)
  expect(requiresOutput('move_by_creation_range')).toBe(true)
  expect(requiresOutput('creation_from_modified')).toBe(false)
})

it('calculates safe progress for empty and active jobs', () => {
  expect(autoInputProgress({ typed_characters: 0, total_characters: 0 })).toBe(0)
  expect(autoInputProgress({ typed_characters: 2, total_characters: 4 })).toBe(50)
})
```

- [ ] **Step 2: Run tests and verify RED**

Run: `npm run test:unit -- src/toolbox/file-time.test.ts src/toolbox/auto-input.test.ts`

Expected: module import failures.

- [ ] **Step 3: Implement types, API clients, and helpers**

Use `/api/toolbox/...` endpoints, shared JSON error extraction, encoded job IDs, clamped percentage values, and discriminated operation/status unions.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `npm run test:unit -- src/toolbox/file-time.test.ts src/toolbox/auto-input.test.ts`

Expected: all focused tests pass.

---

### Task 7: File Time workbench page

**Files:**
- Create: `Agent-vue/src/views/FileTimeView.vue`
- Modify: `Agent-vue/src/router/index.ts`

**Interfaces:**
- Consumes: Task 6 API clients and helpers.
- Produces: authenticated route `/toolbox/file-time`.

- [ ] **Step 1: Implement control-rack state and native folder selection**

Maintain selected operation, editable paths, date values, preview, job, loading state, and polling timer. Selecting a directory uses the backend picker and leaves the existing value unchanged when cancelled.

- [ ] **Step 2: Implement preview-confirm-execute flow**

Disable execution until preview matches current parameters. Any parameter edit invalidates the preview. Poll active jobs every 500 ms until a terminal state and clear timers on unmount.

- [ ] **Step 3: Implement industrial UI**

Use a two-column control-rack/report layout, operation selector cards, path rails, scan summary, sample path list, status counters, progress line, and a confirmation surface. Keep responsive behavior usable below 900 px.

- [ ] **Step 4: Run type-check/build**

Run: `npm run build`

Expected: `vue-tsc` and Vite build succeed.

---

### Task 8: Auto Type workbench page

**Files:**
- Create: `Agent-vue/src/views/AutoInputView.vue`
- Modify: `Agent-vue/src/router/index.ts`

**Interfaces:**
- Consumes: Task 6 automatic-input client and helper.
- Produces: authenticated route `/toolbox/auto-input`.

- [ ] **Step 1: Implement text loading and parameter state**

Read selected `.txt` files through `File.text()`, populate the editor, and expose delay/countdown controls with exact schema limits.

- [ ] **Step 2: Implement start, polling, restore-active, and cancel**

On mount, request the active job. Start returns immediately, polling updates countdown/progress every 250 ms, cancel works in countdown and running states, and terminal states stop polling.

- [ ] **Step 3: Implement industrial UI**

Use a compact left control module and a dominant right editor. Add a full editor progress veil during countdown/running, a visible instruction to switch windows, character counters, a live progress rail, and a high-contrast cancel control.

- [ ] **Step 4: Run type-check/build**

Run: `npm run build`

Expected: `vue-tsc` and Vite build succeed.

---

### Task 9: Toolbox home integration and final verification

**Files:**
- Modify: `Agent-vue/src/views/ToolboxView.vue`
- Modify: `Agent-vue/src/router/index.ts`

**Interfaces:**
- Consumes: routes from Tasks 7 and 8.
- Produces: discoverable Toolbox cards and updated ready-state manifest.

- [ ] **Step 1: Add two real tool cards**

Add `FILE TIME` and `AUTO TYPE` cards with distinct timestamp-grid and blinking-cursor graphics. Mark Voice Lab, File Time, and Auto Type as ready in the manifest.

- [ ] **Step 2: Run the full verification suite**

Run: `.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"`

Run: `npm run test:unit`

Run: `npm run build`

Run: `git diff --check`

Expected: zero backend failures, zero frontend failures, successful production build, and no whitespace errors.

- [ ] **Step 3: Chrome visual verification**

Using the user-required Chrome plugin, inspect `/toolbox`, `/toolbox/file-time`, and `/toolbox/auto-input`; verify desktop and narrow responsive layouts, native-directory buttons, preview gating, text-file loading control, progress layers, and absence of horizontal overflow. Do not execute real file mutations or real automatic typing during visual QA.

- [ ] **Step 4: Leave Git untouched**

Report all changed/untracked files and preserve the current branch for the user's manual commit.

