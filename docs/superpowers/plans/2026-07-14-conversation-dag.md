# Conversation DAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace linear conversation persistence with MongoDB message DAGs supporting retries, edits, version selection, and independent branch conversations.

**Architecture:** Keep FastAPI/Vue API names where practical. Implement a Mongo-first repository over `chat_threads`, `chat_messages`, and `chat_runs`; route/service code calls repository domain operations only. Context is the selected parent chain, never all messages by timestamp.

**Tech Stack:** FastAPI, Pydantic, PyMongo, MongoDB aggregation/transactions where available, Vue 3, TypeScript, Pinia.

## Global Constraints

- Do not delete or read legacy `conversations` and `messages` collections.
- Keep provider settings, user profiles, and existing streamed event types working.
- Do not expose raw chain-of-thought.
- Do not add a generic cross-database ORM; the concrete implementation remains MongoDB-first.

---

### Task 1: DAG schema and repository

**Files:** `AgentBI/src/repositories/chat_repository.py`, `AgentBI/src/services/chat_service.py`, `AgentBI/tests/test_chat_dag.py`

- [ ] Write failing tests for active-path ordering, assistant sibling retry, user sibling edit, and independent branch copy.
- [ ] Implement root/thread/message/run persistence and MongoDB indexes.
- [ ] Run the focused test module to green.

### Task 2: API and streaming integration

**Files:** `AgentBI/src/schemas/chat_schema.py`, `AgentBI/src/api/chat.py`, `AgentBI/src/api/conversations.py`, `AgentBI/tests/test_chat_routes.py`

- [ ] Write failing route/schema tests for DAG fields and endpoints.
- [ ] Route normal sends through active-head context, persist model run snapshots, and add retry/edit/fork/select endpoints.
- [ ] Run all backend tests to green.

### Task 3: Frontend state and message controls

**Files:** `Agent-vue/src/api/chat-types.ts`, `Agent-vue/src/api/chat.ts`, `Agent-vue/src/stores/chat.ts`, `Agent-vue/src/views/ChatView.vue`

- [ ] Extend types/API calls for message versions and branch actions.
- [ ] Refresh state from the server after version changes; add retry, edit, version navigation, and branch-conversation controls.
- [ ] Run type check and production build.

### Task 4: Verification and documentation

**Files:** `docs/AgentBI_开发总览.md`, `docs/子代理模块开发说明.md` only if data-model references require updates.

- [ ] Run backend suite, frontend type check/build, and whitespace diff check.
- [ ] Review that legacy collections are untouched and the active-path context is the only model context source.
