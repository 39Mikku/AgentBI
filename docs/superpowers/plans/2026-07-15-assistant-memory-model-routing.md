# Assistant Memory and Model Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lightweight assistant memory, semantic history retrieval, context compression, model routes, and generated conversation titles without changing original message persistence.

**Architecture:** SQLite remains the only store. `ModelTaskService` performs OpenAI-compatible chat and embedding jobs, while `MemoryService` owns assistant memory, vector retrieval, and context compression. `ChatAgent` receives memory/context system fragments and exposes history search only when enabled.

**Tech Stack:** FastAPI, SQLite, OpenAI Python client, unittest, Vue 3, Pinia, TypeScript.

## Global Constraints

- Never delete or overwrite original chat messages for memory or compression.
- History retrieval is model-decided tool use, not automatic per-turn retrieval.
- Memory updates run only at the assistant-configured interval.
- Do not stage or commit Git changes.

---

### Task 1: Persist model routes and assistant policies

**Files:**
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/src/schemas/assistant_schema.py`
- Create: `AgentBI/src/schemas/model_route_schema.py`
- Create: `AgentBI/src/api/model_routes.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_memory_repository.py`

- [x] Write failing tests for model routes, assistant policy fields, assistant memory, embeddings, and thread summaries.
- [x] Run the focused test and confirm missing repository methods/fields.
- [x] Add the minimal SQLite schema and repository APIs.
- [x] Add model-route REST endpoints and assistant response fields.
- [x] Re-run focused tests.

### Task 2: Add model task and memory services

**Files:**
- Create: `AgentBI/src/services/model_task_service.py`
- Create: `AgentBI/src/services/memory_service.py`
- Modify: `AgentBI/src/services/chat_service.py`
- Test: `AgentBI/tests/test_memory_service.py`

- [x] Write failing tests for cosine filtering, interval decisions, summary injection, and compressed recent context.
- [x] Confirm the tests fail for missing services.
- [x] Implement OpenAI-compatible background chat/embedding calls and pure memory/context helpers.
- [x] Re-run focused tests.

### Task 3: Wire history tool, maintenance, compression, and title events

**Files:**
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/api/chat.py`
- Modify: `AgentBI/src/api/assistants.py`
- Test: `AgentBI/tests/test_chat_agent.py`
- Test: `AgentBI/tests/test_chat_routes.py`

- [x] Write failing tests for conditional history-tool registration and route availability.
- [x] Confirm failures.
- [x] Inject memory and context summaries, execute history lookup, and schedule post-reply maintenance.
- [x] Add assistant memory read/edit/clear/refresh endpoints.
- [x] Re-run focused and full backend tests.

### Task 4: Upgrade model and assistant configuration UI

**Files:**
- Modify: `Agent-vue/src/api/chat-types.ts`
- Modify: `Agent-vue/src/api/assistants.ts`
- Create: `Agent-vue/src/api/model-routes.ts`
- Modify: `Agent-vue/src/views/SettingsView.vue`
- Modify: `Agent-vue/src/views/AssistantsView.vue`
- Modify: `Agent-vue/src/stores/chat.ts`

- [x] Add typed API contracts for model routes, memory, and assistant policy fields.
- [x] Add role selectors to model settings and operational controls plus memory editor to assistant settings.
- [x] Handle `conversation_title_updated` in the chat store.
- [x] Run Vue type checking and production build.

### Task 5: Final verification and documentation

**Files:**
- Modify: `docs/AgentBI_开发总览.md`

- [x] Run all backend tests and Python compilation.
- [x] Run frontend type checking and production build.
- [x] Run `git diff --check` and document runtime behavior and configuration defaults.
