# Atomic Image Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a persistent Lite/Pro atomic image-generation Tool, reusable AI image inputs, independent Codex OAuth, and per-conversation background-generation indicators.

**Architecture:** A single `ImageGenerationService` selects a Lite OpenAI-compatible chat adapter or a Pro Codex OAuth adapter from the user-global capability config. Generated files are stored by `ImageArtifactStore`, represented as timeline cards, and reused through a direct image-generation API by Vue image pickers. Chat background state is tracked by conversation ID.

**Tech Stack:** FastAPI, Pydantic, httpx/OpenAI Python client, SQLite capability settings, Vue 3, Pinia, TypeScript, Vitest, Python unittest/pytest.

## Global Constraints

- One text-to-image result per call; no reference images, editing, or batches.
- Lite calls the selected provider's OpenAI-compatible `/chat/completions`, never `/images/generations`.
- Pro uses a project-owned OAuth file and `gpt-image-2`; it must not mutate Codex CLI/IDE auth.
- Main-chat Tool arguments contain only prompt and aspect ratio; mode and quality remain user configuration.
- Direct avatar generation uses the user's prompt verbatim and never invokes a text model.
- Do not commit, stage, or push; the user handles Git manually.

---

### Task 1: Image contracts, capability registration, and artifact persistence

**Files:**
- Create: `AgentBI/src/schemas/image_generation_schema.py`
- Create: `AgentBI/src/services/image_generation/__init__.py`
- Create: `AgentBI/src/services/image_generation/artifact_store.py`
- Modify: `AgentBI/src/schemas/capability_settings_schema.py`
- Modify: `AgentBI/src/agents/assistant_registry.py`
- Modify: `.gitignore`
- Test: `AgentBI/tests/test_image_generation_contract.py`

**Interfaces:**
- Produces `ImageGenerationConfig`, `ImageGenerationRequest`, `GeneratedImage`, `ImageArtifactStore.save(...)` and the `generate_image` Tool definition.
- `ImageArtifactStore.save(user_id, scope_id, image_bytes, media_type, metadata)` returns a `GeneratedImage` with a stable `/generated-images/...` URL.

- [ ] Write failing tests asserting defaults (`lite`, empty Lite model, Pro `high`), valid aspect ratios, one registered Tool with `prompt` and `aspect_ratio`, safe user hashing, and explicit OAuth ignore rules.
- [ ] Run `python -m pytest AgentBI/tests/test_image_generation_contract.py -q` and verify failure is caused by missing contracts.
- [ ] Implement the Pydantic contracts, registry schema, artifact store, and ignore rules.
- [ ] Re-run the targeted test and verify it passes.

### Task 2: Lite image adapter

**Files:**
- Create: `AgentBI/src/services/image_generation/lite_adapter.py`
- Test: `AgentBI/tests/test_image_generation_lite.py`

**Interfaces:**
- Consumes a provider record, configured model, prompt, and aspect ratio.
- Produces decoded image bytes plus MIME type and upstream model metadata.

- [ ] Write failing async tests for `/chat/completions` request shape and parsers covering `message.images`, content image parts, Data URLs, and malformed/non-image responses.
- [ ] Run `python -m pytest AgentBI/tests/test_image_generation_lite.py -q` and verify RED.
- [ ] Implement a non-streaming OpenAI-compatible chat request with `modalities: ["text", "image"]`, tolerant response extraction, strict Base64/MIME validation, and no `/images/generations` usage.
- [ ] Re-run the targeted test and verify GREEN.

### Task 3: Independent Codex OAuth and Pro adapter

**Files:**
- Create: `AgentBI/src/services/image_generation/codex_oauth.py`
- Create: `AgentBI/src/services/image_generation/codex_adapter.py`
- Test: `AgentBI/tests/test_image_generation_codex.py`

**Interfaces:**
- `CodexOAuthStore.status()`, `start_login()`, `disconnect()`, and `valid_access_token()` own `AgentBI/data/codex-image-oauth.json`.
- `CodexImageAdapter.generate(...)` posts to the Codex Responses stream and returns the final `gpt-image-2` image.

- [ ] Write failing tests for device-code login, independent token persistence, refresh-token rotation, account-ID extraction, required `image_generation` tool request, SSE partial/final image parsing, and token redaction.
- [ ] Run `python -m pytest AgentBI/tests/test_image_generation_codex.py -q` and verify RED.
- [ ] Implement the device-code login flow, refresh logic, atomic secret-file writes, Codex request headers/body, and SSE parser.
- [ ] Re-run the targeted test and verify GREEN.

### Task 4: Service, atomic Tool, API, and timeline card

**Files:**
- Create: `AgentBI/src/services/image_generation/service.py`
- Create: `AgentBI/src/tools/image_generation_tools.py`
- Create: `AgentBI/src/api/image_generation.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/api/chat.py`
- Modify: `AgentBI/src/services/chat_service.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_image_generation_service.py`
- Test: `AgentBI/tests/test_image_generation_api.py`
- Modify: `AgentBI/tests/test_chat_agent.py`
- Modify: `AgentBI/tests/test_chat_core.py`

**Interfaces:**
- `ImageGenerationService.generate(user_id, scope_id, prompt, aspect_ratio, provider=None)` returns `GeneratedImage`.
- Direct Tool returns a compact model-visible JSON string and an optional `image.generated` card.
- `POST /image-generation/generate` accepts direct prompts; OAuth endpoints expose start/status/disconnect without returning tokens.

- [ ] Write failing tests for mode routing, Lite provider requirements, verbatim direct prompts, compact Tool results, card emission order, API validation, static media serving, and OAuth status redaction.
- [ ] Run the new backend tests and verify RED.
- [ ] Implement dependency wiring, Tool invocation with the current provider, card emission, direct API routes, and static media mount.
- [ ] Re-run the targeted tests and verify GREEN.

### Task 5: Capability configuration and OAuth UI

**Files:**
- Create: `Agent-vue/src/api/image-generation-types.ts`
- Create: `Agent-vue/src/api/image-generation.ts`
- Modify: `Agent-vue/src/api/chat-types.ts`
- Modify: `Agent-vue/src/views/SubagentSettingsView.vue`
- Test: `Agent-vue/src/api/image-generation.test.ts`

**Interfaces:**
- Produces typed direct-generation and OAuth API functions.
- Capability page renders mode/model/quality fields plus Codex connect/disconnect controls.

- [ ] Write failing Vitest tests for request payloads, OAuth response typing, and safe popup/polling state transitions.
- [ ] Run `npm run test:unit -- src/api/image-generation.test.ts` in `Agent-vue` and verify RED.
- [ ] Implement the API client and a dedicated image-capability configuration block that matches the existing editorial dark capability page.
- [ ] Re-run the targeted Vitest test and verify GREEN.

### Task 6: Reusable image source picker and existing avatar integrations

**Files:**
- Create: `Agent-vue/src/components/ImageSourcePicker.vue`
- Create: `Agent-vue/src/components/ImageSourcePicker.test.ts`
- Modify: `Agent-vue/src/views/AssistantsView.vue`
- Modify: `Agent-vue/src/views/LiveView.vue`
- Modify: `Agent-vue/src/views/ChatView.vue`

**Interfaces:**
- `ImageSourcePicker` accepts `userId`, optional `providerId`, current `modelValue`, shape, size limit, and theme variables; emits a Data URL through `update:modelValue`.
- AI mode sends the description exactly as entered to the direct image API.

- [ ] Write failing component tests for upload validation, tab switching, verbatim AI prompt submission, loading/error states, and emitted Data URL.
- [ ] Run the component test and verify RED.
- [ ] Implement the picker with focused upload/AI modes and integrate it into assistant, Live role, and user-profile avatar editors.
- [ ] Re-run the component test and verify GREEN.

### Task 7: Image timeline card and per-conversation generation indicators

**Files:**
- Create: `Agent-vue/src/components/cards/ImageGenerationCard.vue`
- Modify: `Agent-vue/src/components/cards/TimelineCard.vue`
- Modify: `Agent-vue/src/utils/card-events.ts`
- Modify: `Agent-vue/src/stores/chat.ts`
- Modify: `Agent-vue/src/views/ChatView.vue`
- Create: `Agent-vue/src/stores/chat-generation-state.test.ts`

**Interfaces:**
- `generatingConversationIds` tracks the originating conversation for the lifetime of each stream.
- `isConversationGenerating(id)` drives the sidebar signal and current-composer stop state.

- [ ] Write failing tests proving state stays attached to the source conversation across selection changes and is cleared on done, error, abort, and thrown request failures.
- [ ] Run the store test and verify RED.
- [ ] Implement ID-based generation state, sidebar motion/copy, and the persistent image card with preview and download but no regeneration action.
- [ ] Re-run the store test and verify GREEN.

### Task 8: Regression and integration verification

**Files:**
- Modify only files required by failures found during verification.

- [ ] Run `python -m pytest AgentBI/tests -q` and resolve any regressions through failing regression tests first.
- [ ] Run `npm run test:unit` in `Agent-vue`.
- [ ] Run `npm run type-check` and `npm run build` in `Agent-vue`.
- [ ] Run `git diff --check` and verify no secret/token/Base64 fixture or generated image is tracked.
- [ ] With the user's configured real provider, perform one Lite generation and verify chat persistence, direct avatar generation, download, and background conversation indicator. If Codex OAuth is connected, perform one Pro generation; otherwise verify the complete login/status flow without exposing credentials.
