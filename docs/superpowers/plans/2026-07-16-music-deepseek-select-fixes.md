# Music, DeepSeek Reasoning, and Model Select Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore reliable NetEase Cloud Music search, add a playable liked-songs list, expose correct DeepSeek V4 reasoning modes, and make native model selectors readable.

**Architecture:** Keep the bundled NetEase API process and existing music cards, fixing protocol selection in the Python client and adding liked-song retrieval behind the music subagent. Centralize model-specific reasoning request options in a focused backend helper and mirror its model-dependent choices in a focused frontend utility. Retain native selects and explicitly style their popup options.

**Tech Stack:** FastAPI, Python 3, httpx, OpenAI-compatible Chat Completions, Vue 3, Pinia, TypeScript, unittest/Vitest.

## Global Constraints

- Do not stage, commit, push, or overwrite unrelated working-tree changes.
- Preserve the current Studio message timeline and music card formats.
- DeepSeek V4 UI modes are `off`, `low`, and `high`, mapped to thinking disabled, `reasoning_effort=high`, and `reasoning_effort=max`.
- Gemini keeps its existing low, medium, and high controls.
- NetEase search must use the verified `weapi` path; do not patch vendored package source.

---

### Task 1: NetEase Search and Liked Songs

**Files:**
- Modify: `AgentBI/src/services/netease_music_client.py`
- Modify: `AgentBI/src/tools/music_tools.py`
- Modify: `AgentBI/src/agents/music_agent.py`
- Modify: `AgentBI/src/schemas/capability_settings_schema.py`
- Test: `AgentBI/tests/test_netease_music_client.py`
- Test: `AgentBI/tests/test_music_agent.py`

**Interfaces:**
- Produces: `NeteaseMusicClient.liked_tracks(limit: int) -> list[MusicTrack]`.
- Produces: `liked_tracks(client, limit) -> MusicToolResult` and a `liked_tracks` music-subagent tool.

- [ ] **Step 1: Add failing client tests**

Add assertions that search sends `crypto=weapi`, and that liked songs are loaded through authenticated account UID plus the special liked playlist and normalized song details.

- [ ] **Step 2: Run the focused client tests and confirm failure**

Run: `python -m unittest AgentBI.tests.test_netease_music_client -v`

Expected: the crypto assertion and missing `liked_tracks` behavior fail.

- [ ] **Step 3: Implement the minimal client behavior**

Make search include `crypto=weapi` and an upstream timeout below the outer httpx timeout. Resolve the authenticated profile, locate the playlist with `specialType == 5`, then request `/playlist/track/all` with the configured limit and normalize `songs`.

- [ ] **Step 4: Add failing music-subagent tests**

Assert the new `liked_tracks` definition is exposed, uses an independent `liked_result_limit`, and produces a `music.track-list` card titled `我喜欢的音乐`.

- [ ] **Step 5: Implement music tool, agent routing, and configuration**

Add `liked_result_limit` with range 1 through 100, wire the subagent tool, and reuse the existing card payload without adding a new frontend card type.

- [ ] **Step 6: Run focused music tests**

Run: `python -m unittest AgentBI.tests.test_netease_music_client AgentBI.tests.test_music_agent AgentBI.tests.test_subagent_settings -v`

Expected: all focused music and settings tests pass.

### Task 2: DeepSeek V4 Reasoning Modes

**Files:**
- Create: `AgentBI/src/services/model_reasoning.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/schemas/chat_schema.py`
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `Agent-vue/src/api/chat.ts`
- Modify: `Agent-vue/src/api/chat-types.ts`
- Create: `Agent-vue/src/utils/model-reasoning.ts`
- Modify: `Agent-vue/src/views/ChatView.vue`
- Test: `AgentBI/tests/test_model_reasoning.py`
- Test: `AgentBI/tests/test_chat_agent.py`
- Test: `Agent-vue/src/utils/model-reasoning.test.ts`

**Interfaces:**
- Produces: `model_reasoning_request_options(model, level) -> dict`.
- Produces: model-aware frontend choices and normalized persisted reasoning level.

- [ ] **Step 1: Add failing backend reasoning tests**

Cover Gemini unchanged behavior and DeepSeek V4 mappings: off disables thinking, low sends `reasoning_effort=high`, high sends `reasoning_effort=max`, while unrelated DeepSeek names receive no V4-only parameters.

- [ ] **Step 2: Run backend reasoning tests and confirm failure**

Run: `python -m unittest AgentBI.tests.test_model_reasoning AgentBI.tests.test_chat_agent -v`

Expected: missing model-aware helper and reasoning-content continuation assertions fail.

- [ ] **Step 3: Implement model-aware request options and tool-loop continuation**

Replace the Gemini-only request hook with the generic helper. Accumulate streamed `reasoning_content` and include it on the assistant tool-call message so DeepSeek tool continuation remains valid.

- [ ] **Step 4: Expand preference validation**

Allow persisted values `off`, `low`, `medium`, and `high`; keep `medium` as the storage default and normalize incompatible values in the frontend when the selected model family changes.

- [ ] **Step 5: Add failing frontend utility tests**

Assert Gemini choices are low/medium/high, DeepSeek V4 choices are off/low/high, and switching models normalizes DeepSeek `medium` to `low` and Gemini `off` to `medium`.

- [ ] **Step 6: Implement and render model-aware controls**

Use the utility in `ChatView.vue`, change the accessible label to generic `推理强度`, and keep the existing visual control.

- [ ] **Step 7: Run focused backend and frontend tests**

Run: `python -m unittest AgentBI.tests.test_model_reasoning AgentBI.tests.test_chat_agent -v`

Run: `npm run test:unit -- --run src/utils/model-reasoning.test.ts`

Expected: both suites pass.

### Task 3: Readable Native Model Selectors

**Files:**
- Modify: `Agent-vue/src/views/SettingsView.vue`

**Interfaces:**
- Produces: native model and provider selects with a dark popup palette and readable option text.

- [ ] **Step 1: Add explicit native select colors**

Set `color-scheme: dark` on settings selects and explicitly style `option` with a dark background and light foreground, including disabled text.

- [ ] **Step 2: Run frontend static verification**

Run: `npm run type-check`

Expected: TypeScript/Vue type checking passes.

- [ ] **Step 3: Verify in Chrome**

Open `http://localhost:5173/settings/models` in the user's Chrome session, open the provider and model selects, and confirm options are readable in normal and disabled states.

### Task 4: Regression Verification

**Files:**
- No additional production files.

**Interfaces:**
- Consumes all prior task outputs.

- [ ] **Step 1: Run relevant backend regression tests**

Run: `python -m unittest AgentBI.tests.test_netease_music_client AgentBI.tests.test_music_agent AgentBI.tests.test_subagent_settings AgentBI.tests.test_model_reasoning AgentBI.tests.test_chat_agent -v`

Expected: all tests pass.

- [ ] **Step 2: Run frontend tests and build**

Run: `npm run test:unit -- --run src/utils/model-reasoning.test.ts`

Run: `npm run type-check`

Run: `npm run build`

Expected: tests, type checking, and production build pass.

- [ ] **Step 3: Perform small live probes**

Verify NetEase search returns results through the bundled service and liked-song retrieval identifies the authenticated account's liked playlist without logging Cookie or account data.

