# Live Voice Enrollment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add URL-based Qwen-Audio-Realtime voice enrollment to Voice Lab and synchronize model-bound cloned voices into Live role configuration.

**Architecture:** A focused Bailian enrollment adapter accepts a validated HTTPS audio URL and returns a voice ID. The existing SQLite voice catalog stores the friendly name, exact Live target model, and remote ID; Voice Lab and Live consume that shared catalog, while Live rejects catalog voices bound to a different model.

**Tech Stack:** FastAPI, Pydantic v2, httpx, SQLite, Vue 3, TypeScript, Pinia, Vitest, unittest.

## Global Constraints

- Do not add OSS SDKs or upload files from the application.
- Never persist or echo the signed source audio URL.
- Support only `qwen-audio-3.0-realtime-flash` and `qwen-audio-3.0-realtime-plus` for Live enrollment.
- Display friendly voice names while provider calls use the returned voice ID.
- Preserve the existing manual Live Voice ID workflow.
- Do not stage or commit; the user performs Git operations manually.

---

### Task 1: Enrollment request contract and Bailian adapter

**Files:**
- Modify: `AgentBI/src/schemas/toolbox_tts_schema.py`
- Create: `AgentBI/src/services/toolbox/tts/bailian_voice_enrollment.py`
- Modify: `AgentBI/tests/test_toolbox_tts_contract.py`
- Modify: `AgentBI/tests/test_toolbox_tts_adapters.py`

**Interfaces:**
- Produces: `LiveVoiceEnrollmentRequest` with `user_id`, `display_name`, `target_model`, `prefix`, and `audio_url`.
- Produces: `BailianLiveVoiceEnrollmentAdapter.enroll(payload) -> LiveVoiceEnrollmentResult`.

- [ ] **Step 1: Write failing schema tests** for allowed models, HTTPS URLs, and 1–10 character alphanumeric prefixes.
- [ ] **Step 2: Run** `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_contract` and confirm the new tests fail because the contract does not exist.
- [ ] **Step 3: Implement the strict Pydantic contract** and extend Bailian bound-model validation to include the two Live models.
- [ ] **Step 4: Write failing adapter tests** asserting the exact `voice-enrollment/create_voice` request and `output.voice_id` response parsing, including an error response that does not contain the signed URL.
- [ ] **Step 5: Run** `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_adapters` and confirm the new tests fail because the adapter does not exist.
- [ ] **Step 6: Implement the adapter** with injected httpx-compatible client support, workspace endpoint construction, response parsing, request ID capture, and sanitized errors.
- [ ] **Step 7: Re-run both focused test modules** and confirm they pass.

### Task 2: Enrollment API and catalog persistence

**Files:**
- Modify: `AgentBI/src/api/toolbox_tts.py`
- Modify: `AgentBI/main.py`
- Modify: `AgentBI/tests/test_toolbox_tts_api.py`

**Interfaces:**
- Produces: `POST /toolbox/tts/voices/enroll-live` returning the existing `TtsVoiceResponse`.
- Persists: `provider=bailian`, friendly display name, remote voice ID, exact target model, and metadata containing only usage, prefix, and request ID.

- [ ] **Step 1: Write a failing API test** with an injected enrollment adapter, asserting that the response and SQLite record contain the correct name, ID, model, and metadata but not the source URL.
- [ ] **Step 2: Run** `.\venv\python.exe -m unittest AgentBI.tests.test_toolbox_tts_api` and confirm the route returns 404.
- [ ] **Step 3: Implement the route and application dependency registration**, mapping configuration failures to 503, validation failures to 422, and upstream failures to 502.
- [ ] **Step 4: Re-run the focused API tests** and confirm they pass.

### Task 3: Server-side Live model-binding guard

**Files:**
- Modify: `AgentBI/src/services/live/conversation_service.py`
- Modify: `AgentBI/tests/test_live_conversation_service.py`

**Interfaces:**
- Consumes: role voice ID, current Live preference model, and the user-scoped voice catalog.
- Produces: `LiveWorkspaceError` before provider connection when a registered Live voice is bound to another model.

- [ ] **Step 1: Write failing tests** for matching and mismatched saved Live voice bindings while leaving manual unregistered voice IDs valid.
- [ ] **Step 2: Run** `.\venv\python.exe -m unittest AgentBI.tests.test_live_conversation_service` and confirm the mismatch is currently accepted.
- [ ] **Step 3: Add the minimal catalog lookup and validation** to Live session preparation.
- [ ] **Step 4: Re-run the focused Live tests** and confirm all pass.

### Task 4: Frontend enrollment API and filtering helpers

**Files:**
- Modify: `Agent-vue/src/api/toolbox-tts-types.ts`
- Modify: `Agent-vue/src/api/toolbox-tts.ts`
- Modify: `Agent-vue/src/toolbox/voice-workbench.ts`
- Modify: `Agent-vue/src/toolbox/voice-workbench.test.ts`

**Interfaces:**
- Produces: `enrollLiveVoice(payload)` API function.
- Produces: helpers that return Live catalog options by exact model and map labels to remote IDs.

- [ ] **Step 1: Write failing Vitest cases** proving Flash/Plus isolation and friendly-name/remote-ID mapping.
- [ ] **Step 2: Run** `npm run test:unit -- src/toolbox/voice-workbench.test.ts` from `Agent-vue` and confirm failure for missing helpers.
- [ ] **Step 3: Add request types, API call, and pure filtering helpers** without changing the UI.
- [ ] **Step 4: Re-run the focused Vitest file** and confirm it passes.

### Task 5: Voice Lab enrollment UI

**Files:**
- Modify: `Agent-vue/src/views/VoiceWorkbenchView.vue`

**Interfaces:**
- Consumes: enrollment API and existing catalog refresh.
- Produces: two drawer modes, URL-based Live enrollment form, progress/error/success states, and catalog refresh.

- [ ] **Step 1: Add the “登记已有音色 / Live 音色复刻” mode switch** while preserving the current form.
- [ ] **Step 2: Add fields** for friendly name, exact target model, alphanumeric prefix defaulting to `livevoice`, and signed OSS HTTPS URL.
- [ ] **Step 3: Submit through `enrollLiveVoice`**, clear the signed URL immediately after completion, refresh custom voices, and show a synchronization result without echoing the URL.
- [ ] **Step 4: Refine responsive styling** within the existing precision-audio-lab visual system.
- [ ] **Step 5: Run** `npm run type-check` and fix any Vue/TypeScript failures.

### Task 6: Live catalog synchronization UI

**Files:**
- Modify: `Agent-vue/src/views/LiveView.vue`
- Modify: `Agent-vue/src/live/role-presentation.ts`
- Modify: `Agent-vue/src/live/role-presentation.test.ts`

**Interfaces:**
- Consumes: shared custom voice catalog and current Live model.
- Produces: saved-voice selection by friendly name, manual-ID fallback, incompatibility warning, and call-start guard.

- [ ] **Step 1: Write failing presentation-helper tests** for friendly labels and exact model compatibility.
- [ ] **Step 2: Run** `npm run test:unit -- src/live/role-presentation.test.ts` and confirm the new cases fail.
- [ ] **Step 3: Load the shared voice catalog in LiveView** and render compatible saved voices for the selected Live model.
- [ ] **Step 4: Preserve manual Voice ID entry** and existing saved roles.
- [ ] **Step 5: Add a visible incompatibility warning and disable start/save paths that would use a catalog voice with the wrong model**, without silently changing the role.
- [ ] **Step 6: Re-run focused presentation and Live store tests** and confirm they pass.

### Task 7: Full verification and handoff

**Files:**
- Verify all modified files.

**Interfaces:**
- Produces: fresh evidence that backend, frontend, build, and repository hygiene pass.

- [ ] **Step 1: Run** `.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"` and require zero failures.
- [ ] **Step 2: Run** `npm run test:unit` from `Agent-vue` and require zero failures.
- [ ] **Step 3: Run** `npm run build` from `Agent-vue` and require successful type-check and Vite build.
- [ ] **Step 4: Run** `git diff --check` and inspect `git status --short`; confirm no temporary URL, credential, generated audio, staging, or commits were introduced.
- [ ] **Step 5: If a usable OSS URL is available in the UI, perform one real enrollment smoke test; otherwise report that mocked API coverage passed and leave the real call for the user-provided URL.**

