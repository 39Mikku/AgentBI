# Live Avatar Fallback and Call Title Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove text from the avatar-less Live core and generate default Live conversation titles through the existing title model after a call.

**Architecture:** Keep title generation in a focused `LiveTitleService` that depends on the SQLite repository and `ModelTaskService`. Schedule it from the Live WebSocket cleanup path alongside memory maintenance; keep the recorder and frontend independent of model-provider details.

**Tech Stack:** FastAPI, SQLite, OpenAI-compatible background model routes, Vue 3, Vitest, unittest.

## Global Constraints

- Do not add a separate Live title-model setting; reuse model route role `title`.
- Do not stage or commit changes; the user commits manually.
- Title generation failure must never block call shutdown.

---

### Task 1: Live title generation service

**Files:**
- Create: `AgentBI/src/services/live/title_service.py`
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Test: `AgentBI/tests/test_live_title_service.py`
- Test: `AgentBI/tests/test_live_workspace_repository.py`

**Interfaces:**
- Consumes: `ModelTaskService.complete(user_id, "title", system, prompt)` and complete Live messages.
- Produces: `LiveTitleService.generate_after_call(user_id, role_id, conversation_id) -> dict | None`.

- [ ] **Step 1: Write failing tests**

Test that appending the first Live user message leaves `新语音会话` unchanged. Test that `generate_after_call` uses the first complete user/assistant pair, updates only a default title, sanitizes the model output, and returns `None` when no title model is available.

- [ ] **Step 2: Verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_title_service AgentBI.tests.test_live_workspace_repository`

Expected: `LiveTitleService` missing and the repository still renames from the first user message.

- [ ] **Step 3: Implement minimal title service**

Create `LiveTitleService` with injected `model_tasks`, select complete messages in chronological order, require at least one user/assistant pair, call route `title`, sanitize with the same punctuation policy as Studio, then call `update_live_conversation`.

- [ ] **Step 4: Verify GREEN**

Run the same command and expect all tests to pass.

### Task 2: Schedule title generation after Live calls

**Files:**
- Modify: `AgentBI/src/api/live.py`
- Test: `AgentBI/tests/test_live_session.py`

**Interfaces:**
- Consumes: `PreparedLiveCall.recorder.has_new_complete_messages` and `LiveTitleService.generate_after_call`.
- Produces: one tracked background title task after a call with new complete messages.

- [ ] **Step 1: Write failing scheduling test**

Patch `LiveTitleService.generate_after_call`, complete a mocked call, execute the tracked task, and assert it receives the current user, role and conversation IDs even when role memory is disabled.

- [ ] **Step 2: Verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_session`

Expected: title service is never scheduled.

- [ ] **Step 3: Implement tracked background task**

Generalize the Live maintenance task tracker or add a matching title scheduler. Catch and log exceptions without affecting WebSocket closure. Keep memory scheduling independent.

- [ ] **Step 4: Verify GREEN**

Run the session tests and expect all tests to pass.

### Task 3: Avatar-less main sound field

**Files:**
- Modify: `Agent-vue/src/components/live/LiveAvatarCore.vue`
- Create: `Agent-vue/src/components/live/LiveAvatarCore.test.ts`

**Interfaces:**
- Consumes: optional role avatar URL.
- Produces: image only when configured; no name-derived text fallback in the main core.

- [ ] **Step 1: Write failing presentation test**

Extract or test a pure presentation helper indicating that an empty avatar has no fallback label. Verify a named role with no avatar returns an empty center label.

- [ ] **Step 2: Verify RED**

Run: `npm run test:unit -- src/components/live/LiveAvatarCore.test.ts`

Expected: current component still derives and renders initials.

- [ ] **Step 3: Remove the center initials fallback**

Remove `roleInitials` from `LiveAvatarCore`; render an image only when `avatar` is truthy and preserve the core background/wave effects otherwise.

- [ ] **Step 4: Verify GREEN**

Run the targeted frontend test and expect it to pass.

### Task 4: Remove optimistic first-message titles and verify

**Files:**
- Modify: `Agent-vue/src/stores/live.ts`
- Modify: `Agent-vue/src/stores/live.test.ts`

**Interfaces:**
- Consumes: conversation list reload performed by `endCall`.
- Produces: no local title mutation from `user.transcript.final`, plus bounded post-call refresh while a default title remains.

- [ ] **Step 1: Write failing store test**

Emit a final user transcript while the selected title is `新语音会话` and assert the title remains unchanged until the server list is reloaded.

- [ ] **Step 2: Verify RED**

Run: `npm run test:unit -- src/stores/live.test.ts`

Expected: current store changes the title to the transcript.

- [ ] **Step 3: Remove optimistic title mutation**

Delete the `user.transcript.final` title assignment from the socket event callback. After the immediate end-call reload, poll the role's conversation list with a bounded delay while the selected title remains a default value; stop immediately after a generated title appears.

- [ ] **Step 4: Full verification**

Run backend full unittest discovery, frontend unit tests, `npm run type-check`, `npm run build-only`, changed-file lint and `git diff --check`.
