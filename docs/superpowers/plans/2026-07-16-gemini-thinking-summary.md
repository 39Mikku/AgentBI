# Gemini Thinking Summary Implementation Plan

> **For agentic workers:** Execute inline in the current session. Do not use subagents. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit Gemini thought-summary requests, persistent low/medium/high reasoning controls, and real-time structured Markdown rendering in Studio.

**Architecture:** Keep provider-specific request construction in a small backend adapter and keep UI-specific Markdown normalization in a small frontend utility. Reuse the existing `reasoning_summary` SSE and message timeline instead of introducing a second reasoning transport.

**Tech Stack:** FastAPI, Pydantic, SQLite, OpenAI Python SDK, Vue 3, Pinia, TypeScript, Vitest.

## Global Constraints

- Work in the current branch and workspace.
- Do not stage or commit; the user manages Git manually.
- Do not alter unrelated `新建 文本文档.txt`.
- Do not use subagents.
- Only Gemini 2.5/3.x receives Gemini thinking parameters.
- Supported UI levels are exactly `low`, `medium`, and `high`; default is `medium`.

---

### Task 1: Backend Gemini thinking adapter and persistence

**Files:**
- Create: `AgentBI/src/services/gemini_thinking.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/schemas/chat_schema.py`
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/src/api/chat.py`
- Test: `AgentBI/tests/test_gemini_thinking.py`
- Test: `AgentBI/tests/test_chat_repository.py`
- Test: `AgentBI/tests/test_chat_agent.py`

**Interfaces:**
- `supports_gemini_thinking(model: str) -> bool`
- `normalize_thinking_level(value: str | None) -> Literal['low', 'medium', 'high']`
- `gemini_request_options(model: str, thinking_level: str | None) -> dict[str, Any]`

- [ ] Write failing tests for model matching and exact request-body nesting.
- [ ] Run focused tests and confirm missing-module/behavior failures.
- [ ] Implement the pure adapter and apply its options to every chat tool-loop request.
- [ ] Write failing repository/schema tests for `thinking_level` persistence and validation.
- [ ] Add the SQLite column migration, API fields, request propagation, and model snapshot field.
- [ ] Run focused backend tests until green.

### Task 2: Frontend preference and structured reasoning rendering

**Files:**
- Create: `Agent-vue/src/utils/gemini-thinking.ts`
- Create: `Agent-vue/src/utils/gemini-thinking.test.ts`
- Modify: `Agent-vue/src/api/chat-types.ts`
- Modify: `Agent-vue/src/api/chat.ts`
- Modify: `Agent-vue/src/stores/chat.ts`
- Modify: `Agent-vue/src/views/ChatView.vue`

**Interfaces:**
- `isGeminiThinkingModel(model?: string | null): boolean`
- `normalizeReasoningMarkdown(source: string): string`
- `renderReasoningMarkdown(source: string): string`

- [ ] Write failing tests for Gemini matching and bold-line heading conversion.
- [ ] Run focused Vitest and confirm failures are caused by the missing feature.
- [ ] Add the utility, preference mapping, and request payload field.
- [ ] Add a composer-adjacent low/medium/high selector shown only for Gemini thinking models.
- [ ] Render both timeline and fallback reasoning blocks as sanitized Markdown with heading styles.
- [ ] Run focused frontend tests until green.

### Task 3: Full verification

**Files:**
- Verify all changed files above.

- [ ] Run `venv\\python.exe -m unittest discover -s AgentBI/tests` and require zero failures.
- [ ] Run `npm --prefix Agent-vue run test:unit` and require zero failures.
- [ ] Run `npm --prefix Agent-vue run build` and require exit code 0.
- [ ] Run `git diff --check` and inspect `git status --short` without staging anything.

