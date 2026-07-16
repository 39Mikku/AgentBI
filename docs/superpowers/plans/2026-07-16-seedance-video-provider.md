# Seedance Video Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Doubao Seedance 1.0 Pro (`doubao-seedance-1-0-pro-250528`) as a selectable provider in the existing asynchronous video generation tool, including optional current-message image-to-video.

**Architecture:** Keep `VideoGenerationService` as the provider-neutral orchestrator and introduce provider adapters selected from a registry. Persist provider/model/request settings per job so polling survives restarts, while the frontend keeps one timeline card and one capability configuration surface.

**Tech Stack:** Python 3.12, FastAPI, httpx, SQLite, Pydantic, Vue 3, TypeScript, Vitest.

## Global Constraints

- Keep one `generate_video` direct tool.
- Do not expose API keys to the model or frontend.
- Do not commit or stage Git changes; the user commits manually.
- Preserve existing Agnes behavior.
- Seedance image-to-video uses the first image bound to the current user message as a Data URL.

---

### Task 1: Provider-neutral contracts and Ark adapter

**Files:**
- Create: `AgentBI/src/services/video_generation/provider.py`
- Create: `AgentBI/src/services/video_generation/ark_client.py`
- Modify: `AgentBI/src/services/video_generation/agnes_client.py`
- Test: `AgentBI/tests/test_video_generation_ark.py`

**Interfaces:**
- Produces `VideoProvider`, `VideoCreateRequest`, and normalized create/query dictionaries.
- Ark adapter accepts `prompt`, `model`, `ratio`, `duration`, `resolution`, `generate_audio`, `watermark`, and optional `image_data_url`.

- [ ] Write failing tests for Ark request JSON, response ID, status mapping, nested video URL, retryable HTTP failures, and image content.
- [ ] Run `venv\python.exe -m unittest AgentBI.tests.test_video_generation_ark` and observe expected failures.
- [ ] Implement the provider contract and Ark adapter using `/contents/generations/tasks`.
- [ ] Adapt Agnes to the same normalized contract without changing its wire format.
- [ ] Run the adapter tests and existing Agnes client tests.

### Task 2: Persistence and model-specific configuration

**Files:**
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/src/schemas/video_generation_schema.py`
- Modify: `AgentBI/src/schemas/capability_settings_schema.py`
- Test: `AgentBI/tests/test_video_generation_contract.py`
- Test: `AgentBI/tests/test_sqlite_chat_repository.py`

**Interfaces:**
- Adds `provider`, `model`, `resolution`, `generate_audio`, `watermark`, and `use_attached_image` to video jobs.
- Produces validated capability configuration with model-specific defaults.

- [ ] Write failing tests for new columns, persisted job fields, and both providers' configuration values.
- [ ] Run the tests and confirm the missing fields fail.
- [ ] Add idempotent SQLite columns and repository mappings.
- [ ] Expand Pydantic and capability setting schemas without invalidating existing Agnes defaults.
- [ ] Run repository and contract tests.

### Task 3: Provider registry, submission, polling, and attachments

**Files:**
- Modify: `AgentBI/src/services/video_generation/service.py`
- Modify: `AgentBI/src/services/video_generation/__init__.py`
- Modify: `AgentBI/src/tools/video_generation_tools.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/agents/assistant_registry.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_video_generation_service.py`
- Test: `AgentBI/tests/test_video_generation_tool.py`

**Interfaces:**
- `VideoGenerationService` consumes a provider mapping and selects by persisted provider/model.
- `generate_video(..., use_attached_image=False)` passes the current message ID so the service can resolve the image.

- [ ] Write failing tests for provider selection, Seedance status mapping, restart recovery, image attachment transfer, and generated asset metadata.
- [ ] Run the tests and verify failures are caused by the single-client implementation.
- [ ] Refactor submission and polling to use the provider registry.
- [ ] Add current-message image lookup and clear errors for unsupported/missing image references.
- [ ] Initialize both adapters from environment variables and update the tool description.
- [ ] Run service, tool, and chat-agent tests.

### Task 4: Frontend configuration and provider-aware video card

**Files:**
- Modify: `Agent-vue/src/api/video-generation.ts`
- Modify: `Agent-vue/src/components/cards/VideoGenerationCard.vue`
- Modify: `Agent-vue/src/components/cards/TimelineCard.vue`
- Modify: capability settings UI files discovered from `Agent-vue/src/views/SubagentSettingsView.vue`
- Test: `Agent-vue/src/utils/video-generation.test.ts`
- Test: relevant capability-settings tests.

**Interfaces:**
- API job objects expose provider/model/resolution/audio metadata.
- Card labels are provider-neutral and use an indeterminate phase for Ark jobs.

- [ ] Write failing tests for Seedance duration/ratio option derivation and terminal status behavior.
- [ ] Run targeted Vitest tests and confirm expected failures.
- [ ] Add model-dependent capability fields and frontend option filtering.
- [ ] Remove hard-coded Agnes copy/download names from the card and display the persisted model.
- [ ] Run targeted frontend tests and `npm run build`.

### Task 5: Environment and complete verification

**Files:**
- Modify: `AgentBI/.env.example`
- Modify: `AgentBI/.env`

**Interfaces:**
- Adds empty `ARK_API_KEY` and default `ARK_VIDEO_BASE_URL` entries.

- [ ] Add environment placeholders without inserting secrets into source code.
- [ ] Run `venv\python.exe -m unittest discover -s AgentBI/tests`.
- [ ] Run `npm run test:unit` and `npm run build` from `Agent-vue`.
- [ ] Run `git diff --check` and inspect `git status --short` without staging or committing.
