# Agnes Video Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable asynchronous Agnes text-to-video tool with automatic polling, local MP4 download, and an in-conversation progress card.

**Architecture:** The direct tool creates a SQLite-backed job and returns immediately. A lifespan-owned service polls Agnes in the background, downloads completed output into local generated assets, and exposes job state to a Vue card that survives navigation and reloads.

**Tech Stack:** FastAPI, Pydantic, httpx, SQLite, asyncio, Vue 3, TypeScript, Vitest.

## Global Constraints

- Fixed model `agnes-video-v2.0` and text-to-video only.
- Tool arguments are limited to prompt, aspect ratio, and duration.
- Fixed 24 FPS and duration-to-frame mapping: 3→81, 5→121, 10→241, 18→441.
- API key comes from `AGNES_API_KEY`; no user-facing key storage.
- Preserve unrelated worktree changes and leave Git commits to the user.

---

### Task 1: Video contracts and configuration

**Files:**
- Create: `AgentBI/src/schemas/video_generation_schema.py`
- Modify: `AgentBI/src/schemas/capability_settings_schema.py`
- Test: `AgentBI/tests/test_video_generation_contract.py`

**Interfaces:**
- Produces `VideoGenerationConfig`, `VideoGenerationJobResponse`, `frames_for_duration`, and capability fields for `tool.video_generation`.

- [ ] Write tests for accepted ratios, durations, defaults, and exact frame mapping.
- [ ] Run the focused tests and verify they fail because the contracts do not exist.
- [ ] Implement the minimal schemas and configuration registration.
- [ ] Run the focused tests and verify they pass.

### Task 2: Agnes client and durable job repository

**Files:**
- Create: `AgentBI/src/services/video_generation/agnes_client.py`
- Create: `AgentBI/src/services/video_generation/service.py`
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Test: `AgentBI/tests/test_video_generation_service.py`

**Interfaces:**
- `AgnesVideoClient.create_video(...) -> provider task snapshot`
- `AgnesVideoClient.get_video(video_id) -> provider task snapshot`
- `VideoGenerationService.submit(...) -> local job`
- `VideoGenerationService.get_job(job_id, user_id) -> local job | None`

- [ ] Write failing tests for request payloads, SQLite persistence, immediate submission, polling completion, MP4 download, and stale-job recovery.
- [ ] Run the focused tests and verify the expected failures.
- [ ] Implement repository methods, adapter, worker tracking, retry policy, and download persistence.
- [ ] Run the focused tests and verify they pass.

### Task 3: Direct tool, registration, and API

**Files:**
- Create: `AgentBI/src/tools/video_generation_tools.py`
- Create: `AgentBI/src/api/video_generation.py`
- Modify: `AgentBI/src/agents/assistant_registry.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/api/chat.py`
- Modify: `AgentBI/main.py`
- Modify: `AgentBI/.env.example`
- Test: `AgentBI/tests/test_video_generation_tool.py`
- Test: `AgentBI/tests/test_chat_routes.py`

**Interfaces:**
- Direct tool `generate_video` returns compact queued context plus `video.generation` card payload.
- `GET /video-generation/jobs/{job_id}?user_id=...` returns current state.

- [ ] Write failing registration, tool-card, route, and lifecycle tests.
- [ ] Run the focused tests and verify they fail for missing behavior.
- [ ] Wire the service into app lifespan and ChatAgent without blocking the response.
- [ ] Run the focused tests and verify they pass.

### Task 4: Local video assets

**Files:**
- Modify: `AgentBI/src/schemas/studio_asset_schema.py`
- Modify: `AgentBI/src/services/studio_asset_service.py`
- Modify: `AgentBI/src/api/studio_assets.py`
- Modify: `Agent-vue/src/api/chat-types.ts`
- Modify: `Agent-vue/src/views/AttachmentsView.vue`
- Test: `AgentBI/tests/test_studio_assets.py`

**Interfaces:**
- Generated MP4 is registered as `kind="video"` and served inline from the existing asset endpoint.

- [ ] Write failing tests for generated video registration, inline content response, and tombstoning.
- [ ] Run the focused tests and verify the expected failures.
- [ ] Extend asset types and attachment presentation for MP4.
- [ ] Run the focused tests and verify they pass.

### Task 5: Timeline progress card

**Files:**
- Create: `Agent-vue/src/api/video-generation.ts`
- Create: `Agent-vue/src/api/video-generation-types.ts`
- Create: `Agent-vue/src/components/cards/VideoGenerationCard.vue`
- Create: `Agent-vue/src/utils/video-generation.ts`
- Modify: `Agent-vue/src/components/cards/TimelineCard.vue`
- Modify: `Agent-vue/src/views/AssistantsView.vue`
- Modify: `Agent-vue/src/views/SubagentSettingsView.vue`
- Test: `Agent-vue/src/utils/video-generation.test.ts`

**Interfaces:**
- Card receives `job_id`, polls the project API while active, and renders queued, progress, failed, or playable state.

- [ ] Write failing tests for terminal-state detection, poll interval, and progress normalization.
- [ ] Run Vitest and verify the expected failures.
- [ ] Implement API types, card, card dispatch, assistant toggle, settings code, and video attachment preview.
- [ ] Run Vitest and verify the focused tests pass.

### Task 6: Integrated verification

**Files:**
- Modify only files required by failures found during verification.

- [ ] Run all Python tests.
- [ ] Run all Vue tests, type checking, and production build.
- [ ] Run `git diff --check` and inspect only this feature's diff.
- [ ] Use Chrome to verify queued, progress, completed, failed, reload, and cross-conversation behavior when a real Agnes key is available.

