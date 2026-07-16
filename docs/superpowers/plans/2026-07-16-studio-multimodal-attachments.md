# Studio Multimodal Attachments Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent image/DOCX attachments, model-bound vision capabilities, text-model vision fallback, an asset library, and assistant-message Markdown copy to Studio.

**Architecture:** Store binary files on disk and metadata/cache/tombstones in SQLite through a unified `studio_assets` catalog plus message links. Build model input through a dedicated multimodal context service that either emits OpenAI image content blocks or injects cached vision/DOCX text. Keep upload, library, and message rendering behind typed FastAPI/Vue APIs.

**Tech Stack:** FastAPI, SQLite, OpenAI-compatible Chat Completions, `python-docx`, Vue 3, Pinia, TypeScript, Vitest, Python `unittest`.

## Global Constraints

- Supported uploads are PNG, JPEG, WebP, GIF, and DOCX only.
- Image maximum is 10 MB, DOCX maximum is 20 MB, one message maximum is 8 assets and 30 MB total.
- DOCX extraction is capped at 100,000 characters and never appears in the visible user message.
- Model vision support is keyed by `user_id + provider_id + model`; unspecified models default to text-only.
- Vision fallback temperature is `1.0`.
- Deleting an asset removes bytes and all derived text while keeping a tombstone and message links.
- Do not commit, stage, or push; the user handles Git manually.

---

### Task 1: Unified asset catalog and file service

**Files:**
- Modify: `AgentBI/requirements.txt`
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Create: `AgentBI/src/schemas/studio_asset_schema.py`
- Create: `AgentBI/src/services/studio_asset_service.py`
- Test: `AgentBI/tests/test_studio_assets.py`

**Interfaces:**
- Produces `StudioAssetService.upload(user_id, filename, content_type, data)`, `bind_assets(message_id, user_id, asset_ids)`, `list_assets(...)`, `delete_asset(...)`, `content_for(asset)`, and repository CRUD/link methods.
- Produces asset response fields `id`, `source`, `kind`, `filename`, `mime_type`, `size`, `url`, `status`, `metadata`, `created_at`, `deleted_at`.

- [ ] **Step 1: Write failing repository/service tests** covering valid image signatures, DOCX paragraph/table extraction, unsupported/corrupt/oversized input, ownership checks, message links, branch link copying, and tombstone deletion clearing `extracted_text`/`vision_summary`.
- [ ] **Step 2: Run `\.\venv\python.exe -m unittest AgentBI.tests.test_studio_assets`** and confirm failures are caused by missing asset APIs.
- [ ] **Step 3: Add `python-docx>=1.1,<2` and implement schema migration** for `studio_assets` and `chat_message_assets`, including unique message ordering and indexes by user/source/kind/date.
- [ ] **Step 4: Implement the file service** using random IDs, user-hash directories, signature checks, DOCX extraction, controlled URLs, 24-hour orphan cleanup, and tombstone deletion.
- [ ] **Step 5: Copy message-asset links during DAG branch/edit cloning** without duplicating files.
- [ ] **Step 6: Re-run the focused tests** and confirm green.

### Task 2: Asset HTTP API and generated-image registration

**Files:**
- Create: `AgentBI/src/api/studio_assets.py`
- Modify: `AgentBI/main.py`
- Modify: `AgentBI/src/services/image_generation/service.py`
- Modify: `AgentBI/src/tools/image_generation_tools.py`
- Test: `AgentBI/tests/test_studio_asset_api.py`
- Modify: `AgentBI/tests/test_image_generation_service.py`

**Interfaces:**
- Produces `POST /assets`, `GET /assets`, `GET /assets/{id}/content`, `DELETE /assets/{id}`.
- Image generation records `source="generated"` with prompt/model metadata; chat persistence links its asset ID to the assistant message.

- [ ] **Step 1: Write failing API and generation tests** for multipart upload, filters/search, controlled content response, ownership, tombstone deletion, and generated asset registration.
- [ ] **Step 2: Run focused tests** and verify expected failures.
- [ ] **Step 3: Mount `StudioAssetService` in FastAPI lifespan and register the router.**
- [ ] **Step 4: Implement upload/list/content/delete endpoints** with precise 4xx errors and no disk-path leakage.
- [ ] **Step 5: Register successful chat image generations in the asset catalog** and include `asset_id` in `image.generated` card payload without exposing internal paths.
- [ ] **Step 6: Re-run focused tests** and confirm green.

### Task 3: Model-bound vision capability and vision route

**Files:**
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/src/schemas/model_route_schema.py`
- Create: `AgentBI/src/schemas/model_capability_schema.py`
- Create: `AgentBI/src/api/model_capabilities.py`
- Modify: `AgentBI/src/services/model_task_service.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_model_capabilities.py`
- Modify: `AgentBI/tests/test_memory_repository.py`

**Interfaces:**
- Produces `GET/PUT /model-capabilities` and repository methods `get_model_capability`, `set_model_capability`, `list_model_capabilities`.
- Extends `ModelRole` with `vision`.
- Produces `ModelTaskService.describe_images(user_id, images)` returning per-asset descriptions from one multimodal call.

- [ ] **Step 1: Write failing tests** proving exact provider/model binding, default false, provider deletion cleanup, `vision` route acceptance, temperature `1.0`, and one multi-image request.
- [ ] **Step 2: Run focused tests** and confirm missing behavior.
- [ ] **Step 3: Add `model_capabilities` migration and CRUD/API.**
- [ ] **Step 4: Extend model routing with `vision` and implement `describe_images`** using Data URLs, labeled filenames, JSON-first parsing with a safe plain-text fallback.
- [ ] **Step 5: Re-run focused tests** and confirm green.

### Task 4: Multimodal context and chat lifecycle

**Files:**
- Create: `AgentBI/src/services/multimodal_context_service.py`
- Modify: `AgentBI/src/services/chat_service.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/schemas/chat_schema.py`
- Modify: `AgentBI/src/api/chat.py`
- Modify: `AgentBI/src/api/conversations.py`
- Test: `AgentBI/tests/test_multimodal_context.py`
- Modify: `AgentBI/tests/test_chat_routes.py`

**Interfaces:**
- `ChatStreamRequest.content` accepts an empty string only when `attachment_ids` is non-empty.
- User messages expose `assets`; chat input uses `list[dict[str, Any]]` so `content` may be text or OpenAI content blocks.
- Multimodal models receive original image Data URLs; text-only models receive cached hidden descriptions; DOCX always becomes hidden text.

- [ ] **Step 1: Write failing tests** for attachment-only messages, binding, multimodal direct input, text fallback/cache reuse, missing vision route, deleted assets, historical images, and message response assets.
- [ ] **Step 2: Run focused tests** and verify failures.
- [ ] **Step 3: Implement the multimodal context service** over the selected DAG/window/compression bundle, preserving visible message text.
- [ ] **Step 4: Wire send/edit/retry/branch flows** so attachments remain with the correct user message and generated cards link to the active assistant message.
- [ ] **Step 5: Generalize chat-agent message typing** without changing streaming/tool behavior.
- [ ] **Step 6: Re-run focused backend tests** and confirm green.

### Task 5: Vue upload, composer, and message attachment UI

**Files:**
- Create: `Agent-vue/src/api/studio-assets.ts`
- Create: `Agent-vue/src/components/chat/AttachmentComposer.vue`
- Create: `Agent-vue/src/components/chat/MessageAssets.vue`
- Modify: `Agent-vue/src/api/chat-types.ts`
- Modify: `Agent-vue/src/api/chat.ts`
- Modify: `Agent-vue/src/stores/chat.ts`
- Modify: `Agent-vue/src/views/ChatView.vue`
- Test: `Agent-vue/src/api/studio-assets.test.ts`
- Test: `Agent-vue/src/utils/chat-attachments.test.ts`

**Interfaces:**
- Composer emits uploaded asset IDs and blocks send while uploads are pending.
- `ChatMessage.assets` renders persistent thumbnail/document cards; deleted entries render tombstones.

- [ ] **Step 1: Write failing Vitest tests** for multipart API mapping, send payload `attachment_ids`, attachment-only send, limit validation, and deleted/active display state helpers.
- [ ] **Step 2: Run focused Vitest tests** and confirm expected failures.
- [ ] **Step 3: Implement typed asset API and chat payload fields.**
- [ ] **Step 4: Build attachment composer** with previews, progress/error states, removal, limits, and modern Studio styling.
- [ ] **Step 5: Build historical message asset rendering** with bounded image grid, original preview/download, DOCX card, and deleted placeholder.
- [ ] **Step 6: Re-run focused frontend tests and type-check.**

### Task 6: Model workbench and attachment library

**Files:**
- Create: `Agent-vue/src/api/model-capabilities.ts`
- Create: `Agent-vue/src/views/AttachmentsView.vue`
- Modify: `Agent-vue/src/views/SettingsView.vue`
- Modify: `Agent-vue/src/router/index.ts`
- Modify: `Agent-vue/src/views/ChatView.vue`
- Test: `Agent-vue/src/api/model-capabilities.test.ts`
- Test: `Agent-vue/src/utils/asset-library.test.ts`

**Interfaces:**
- Settings adds `vision` to background routing and a per-provider/model visual capability toggle.
- `/attachments` supports source/kind filters, search, preview/download, source-conversation navigation, confirmation, and deletion.

- [ ] **Step 1: Write failing tests** for capability API serialization, asset filters/search query mapping, source navigation, and delete-state behavior.
- [ ] **Step 2: Run focused tests** and confirm failures.
- [ ] **Step 3: Add model-capability loading/toggles and the vision route card** to Model Studio.
- [ ] **Step 4: Implement the attachment library page** with responsive image grid, DOCX rows, empty/loading/error states, and deletion confirmation.
- [ ] **Step 5: Register the route and Studio navigation entry.**
- [ ] **Step 6: Re-run focused tests and type-check.**

### Task 7: Copy Markdown and complete regression

**Files:**
- Create: `Agent-vue/src/utils/clipboard.ts`
- Test: `Agent-vue/src/utils/clipboard.test.ts`
- Modify: `Agent-vue/src/views/ChatView.vue`

**Interfaces:**
- `copyMarkdown(text)` writes raw message content and reports success/failure; UI shows a transient “已复制”.

- [ ] **Step 1: Write a failing clipboard test** proving raw Markdown is copied unchanged and clipboard errors are surfaced.
- [ ] **Step 2: Run the focused test** and confirm failure.
- [ ] **Step 3: Implement the helper and add “复制 MD” beside retry/branch** for completed assistant messages only.
- [ ] **Step 4: Run `\.\venv\python.exe -m unittest discover -s AgentBI/tests`.**
- [ ] **Step 5: Run `npm --prefix Agent-vue run test:unit`.**
- [ ] **Step 6: Run `npm --prefix Agent-vue run build` and `git diff --check`.**
- [ ] **Step 7: Review `git status --short` and leave all changes unstaged for the user.**

