# Live 角色、会话与记忆系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有单次 Live 通话页升级为拥有独立角色、角色会话列表、可恢复历史上下文、角色头像、自定义音色和通话结束后长期记忆维护的完整语音工作区。

**Architecture:** Live 使用独立 SQLite 表保存角色、线程、消息与记忆，公共配置仍保存在 `live_preferences`。FastAPI 在建立百炼连接时从数据库解析角色与历史，严格按 session 配置、角色记忆、历史消息、ready 的顺序准备上游会话；最终转写由连接级记录器持久化，角色记忆在挂断后通过已有 memory 模型路由异步更新。Vue 将运行时音频状态与持久工作区状态组合在一个 Pinia store 中，并把大型页面拆成职责清晰的 Live 子组件。

**Tech Stack:** Python 3.11、FastAPI、Pydantic v2、SQLite、`websockets`、Vue 3、Pinia、TypeScript、Web Audio/AudioWorklet、Vitest、`unittest`。

## Global Constraints

- 继续使用当前分支和当前 checkout；不创建 worktree。
- 不执行 `git add`、`git commit` 或任何自动提交，项目所有者手动提交。
- Live 不复用 Studio 的 Assistant、Chat Thread、Message DAG、Tool、Agent 或 RAG 数据表。
- Live 可以复用 `ModelTaskService` 的 `memory` 模型路由和 SQLite 连接基础设施。
- 公共历史注入配置使用 `history_context_turns=0` 表示“全部”，其余合法值为 1 至 50。
- 百炼 `max_history_turns` 合法值为 1 至 50，默认 20。
- 新建 Live 会话永远不注入历史；继续已有会话才按公共配置注入。
- 关闭角色记忆不删除记忆，只停止注入和自动更新。
- 内置与复刻音色共用一个非空 `voice` 字符串，长度不超过 128。
- 通话期间禁止切换角色、切换会话或修改连接关键配置。
- 每个生产行为必须先有一个因该行为缺失而失败的测试。

---

### Task 1: Live 独立 SQLite 数据域

**Files:**
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/tests/test_live_preferences.py`
- Create: `AgentBI/tests/test_live_workspace_repository.py`

**Interfaces:**
- Produces: `ensure_default_live_role(user_id: str) -> dict[str, Any]`
- Produces: `list_live_roles(user_id: str) -> list[dict[str, Any]]`
- Produces: `create_live_role(payload: dict[str, Any]) -> dict[str, Any]`
- Produces: `update_live_role(role_id: str, user_id: str, fields: dict[str, Any]) -> dict[str, Any] | None`
- Produces: `delete_live_role(role_id: str, user_id: str) -> bool`
- Produces: Live conversation, message and role-memory CRUD methods used by later services.

- [ ] **Step 1: Write failing public-preference migration tests**

```python
def test_live_preferences_keep_only_public_call_settings(self):
    prefs = self.repo.get_live_preferences("alice")
    self.assertEqual(prefs["model"], "qwen-audio-3.0-realtime-flash")
    self.assertEqual(prefs["history_context_turns"], 12)
    self.assertEqual(prefs["max_history_turns"], 20)

def test_default_role_inherits_legacy_voice_and_instructions(self):
    role = self.repo.ensure_default_live_role("alice")
    self.assertEqual(role["voice"], "longanqian")
    self.assertTrue(role["instructions"])
```

- [ ] **Step 2: Run the preference tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_preferences -v`

Expected: failure because the two public fields and default Live role do not exist.

- [ ] **Step 3: Write failing workspace repository tests**

```python
def test_roles_own_independent_conversation_lists(self):
    left = self.repo.create_live_role({"user_id": "alice", "name": "A", "instructions": "A", "voice": "longanqian"})
    right = self.repo.create_live_role({"user_id": "alice", "name": "B", "instructions": "B", "voice": "custom-voice-id"})
    self.repo.create_live_conversation({"user_id": "alice", "role_id": left["id"]})
    self.assertEqual(len(self.repo.list_live_conversations("alice", left["id"])), 1)
    self.assertEqual(self.repo.list_live_conversations("alice", right["id"]), [])

def test_interrupted_messages_are_visible_but_not_replayable(self):
    thread = self._thread()
    self.repo.append_live_message(thread["id"], "alice", thread["role_id"], "assistant", "partial", "a1", "interrupted")
    self.assertEqual(len(self.repo.list_live_messages(thread["id"], "alice")), 1)
    self.assertEqual(self.repo.list_live_replay_messages(thread["id"], "alice", 0), [])
```

- [ ] **Step 4: Run workspace tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_workspace_repository -v`

Expected: failure because Live role, conversation, message and memory methods do not exist.

- [ ] **Step 5: Add schema and repository implementation**

Add tables `live_roles`, `live_threads`, `live_messages`, and `live_role_memories`; add `history_context_turns` and `max_history_turns` columns to `live_preferences` through `_ensure_column`. Keep legacy `voice` and `instructions` columns for SQLite compatibility, but expose them only as the initial default-role seed.

Use these stable defaults:

```python
DEFAULT_LIVE_PREFERENCES = {
    "model": "qwen-audio-3.0-realtime-flash",
    "history_context_turns": 12,
    "max_history_turns": 20,
}
```

The replay query must order chronologically, exclude `status != 'complete'`, and keep complete QA pairs when limiting by turns.

- [ ] **Step 6: Rerun repository tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_preferences AgentBI.tests.test_live_workspace_repository -v`

Expected: all tests pass.

### Task 2: Live REST schemas and workspace API

**Files:**
- Modify: `AgentBI/src/api/live.py`
- Create: `AgentBI/tests/test_live_workspace_api.py`
- Modify: `AgentBI/tests/test_chat_routes.py`

**Interfaces:**
- Produces the role, role-memory, Live conversation and Live message endpoints listed in the approved design.
- Changes `LivePreferencesUpdate` to public fields only.
- Changes `LiveSessionStart` to `{type, role_id, conversation_id?}`.

- [ ] **Step 1: Write failing schema tests**

```python
def test_public_preferences_validate_both_history_limits(self):
    payload = LivePreferencesUpdate(
        model="qwen-audio-3.0-realtime-flash",
        history_context_turns=0,
        max_history_turns=50,
    )
    self.assertEqual(payload.history_context_turns, 0)
    with self.assertRaises(ValidationError):
        LivePreferencesUpdate(model="qwen-audio-3.0-realtime-flash", history_context_turns=51, max_history_turns=20)

def test_custom_voice_is_accepted_but_blank_voice_is_rejected(self):
    self.assertEqual(LiveRoleCreate(user_id="alice", name="角色", instructions="提示", voice="clone-001").voice, "clone-001")
    with self.assertRaises(ValidationError):
        LiveRoleCreate(user_id="alice", name="角色", instructions="提示", voice=" ")
```

- [ ] **Step 2: Write failing API ownership and CRUD tests**

Use `TestClient(app)` with an in-memory repository and assert that Alice cannot read or update Bob's role, conversation, messages or memory. Assert default roles cannot be deleted and non-default roles can be deleted only when no active database dependency blocks them.

- [ ] **Step 3: Run the new API tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_workspace_api AgentBI.tests.test_chat_routes -v`

Expected: missing schema and route failures.

- [ ] **Step 4: Implement Pydantic models and REST routes**

Use focused helper functions for ownership resolution and return HTTP 404 for missing or foreign resources. Role update fields are `name`, `instructions`, `voice`, `avatar_data_url`, and `memory_enabled`. Conversation update accepts only `title`.

- [ ] **Step 5: Rerun API tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_workspace_api AgentBI.tests.test_chat_routes -v`

Expected: all tests pass.

### Task 3: Deterministic history and memory injection before ready

**Files:**
- Create: `AgentBI/src/services/live/context.py`
- Modify: `AgentBI/src/services/live/qwen_audio_realtime.py`
- Modify: `AgentBI/src/services/live/protocol.py`
- Modify: `AgentBI/tests/test_live_session.py`
- Create: `AgentBI/tests/test_live_context.py`

**Interfaces:**
- Produces: `build_live_context_items(memory: str | None, messages: list[dict[str, Any]]) -> list[dict[str, Any]]`
- Extends: `LiveSessionConfig(model, voice, instructions, max_history_turns)`.
- Extends: `QwenAudioRealtimeSession.run(frontend, config, context_items, event_handler=None)`.

- [ ] **Step 1: Write failing context-item tests**

```python
def test_memory_precedes_chronological_history(self):
    items = build_live_context_items("用户喜欢咖啡", [
        {"role": "user", "content": "继续昨天的话题"},
        {"role": "assistant", "content": "可以"},
    ])
    self.assertEqual(items[0]["item"]["role"], "system")
    self.assertEqual([item["item"]["role"] for item in items[1:]], ["user", "assistant"])
```

- [ ] **Step 2: Run context tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_context -v`

Expected: module missing.

- [x] **Step 3: Implement provider-compatible context composition**

Compose the selected history and memory into stable `<role_memory>` and `<conversation_history>` sections appended to the role instructions.

- [ ] **Step 4: Write failing session ordering tests**

The injected fake upstream must acknowledge `session.update` with `session.updated`. Assert outbound order is:

```text
session.update(with role prompt + memory + history)
frontend session.ready
input_audio_buffer.append
```

Also assert `max_history_turns` is copied into `session.update` and no microphone frame is forwarded before preparation completes.

- [ ] **Step 5: Run session tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_session -v`

Expected: persisted memory and history are absent from session instructions.

- [ ] **Step 6: Implement acknowledged preparation and event hook**

Compose role memory and the selected complete history turns into `session.instructions`, then wait for `session.updated` before sending the internal `session.ready`. Do not replay ordinary messages with `conversation.item.create`: the current BaiLian Audio Realtime contract only accepts `function_call_output` items there. Only after ready may the bidirectional forwarding tasks start.

- [ ] **Step 7: Rerun protocol and session tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_context AgentBI.tests.test_live_protocol AgentBI.tests.test_live_session -v`

Expected: all tests pass.

### Task 4: Call recording and end-of-call role memory maintenance

**Files:**
- Create: `AgentBI/src/services/live/conversation_service.py`
- Create: `AgentBI/src/services/live/memory_service.py`
- Modify: `AgentBI/src/api/live.py`
- Create: `AgentBI/tests/test_live_conversation_service.py`
- Create: `AgentBI/tests/test_live_memory_service.py`

**Interfaces:**
- Produces: `LiveConversationService.prepare(user_id, role_id, conversation_id) -> PreparedLiveCall`.
- Produces: `LiveCallRecorder.handle(event: LiveEvent) -> LiveEvent`.
- Produces: `LiveMemoryService.update_after_call(user_id, role_id, last_message_id) -> dict[str, Any] | None`.
- Produces: `LiveMemoryService.refresh(user_id, role_id) -> dict[str, Any] | None`.

- [ ] **Step 1: Write failing preparation tests**

Assert a missing or foreign role/conversation fails before the upstream connector is opened. Assert new conversations return no replay items, existing conversations use `history_context_turns`, and disabled memory returns no memory item without clearing stored memory.

- [ ] **Step 2: Write failing recorder tests**

Feed user final, assistant deltas, assistant final and response interruption events to a recorder. Assert deltas do not create rows, finals create exactly one row, repeated finals are idempotent by `item_id`, and interruption persists the current assistant buffer with `status='interrupted'`.

- [ ] **Step 3: Run conversation tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_conversation_service -v`

Expected: service classes do not exist.

- [ ] **Step 4: Implement call preparation and recording**

`PreparedLiveCall` contains resolved role, preferences, thread, and a `LiveSessionConfig` whose instructions already include the selected memory/history context. The recorder enriches final normalized events with `message_id` and `conversation_id`, updates a first-message local title, and exposes whether this call produced new complete messages.

- [ ] **Step 5: Write failing memory maintenance tests**

```python
async def test_disabled_memory_is_neither_injected_nor_updated(self):
    result = await service.update_after_call("alice", role_id, last_message_id)
    self.assertIsNone(result)
    self.assertEqual(repository.get_live_role_memory("alice", role_id)["content"], "keep me")

async def test_one_call_makes_at_most_one_memory_completion(self):
    await service.update_after_call("alice", role_id, last_message_id)
    self.assertEqual(model_tasks.calls, 1)
```

- [ ] **Step 6: Run memory tests and verify RED**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_memory_service -v`

Expected: memory service missing.

- [ ] **Step 7: Implement Live memory service and WebSocket orchestration**

Reuse `ModelTaskService.complete(user_id, "memory", system, prompt)`. Save memory only on non-empty success. In the WebSocket route, close the frontend connection first, then schedule one tracked background task only when the recorder reports new complete messages and the role memory switch is enabled. Consume task exceptions into safe logs.

- [ ] **Step 8: Rerun Live backend tests and verify GREEN**

Run: `.\venv\python.exe -m unittest AgentBI.tests.test_live_conversation_service AgentBI.tests.test_live_memory_service AgentBI.tests.test_live_session -v`

Expected: all tests pass.

### Task 5: Frontend API, nonlinear history slider and workspace store

**Files:**
- Modify: `Agent-vue/src/api/live-types.ts`
- Modify: `Agent-vue/src/api/live.ts`
- Create: `Agent-vue/src/live/history-context.ts`
- Create: `Agent-vue/src/live/history-context.test.ts`
- Modify: `Agent-vue/src/stores/live.ts`
- Modify: `Agent-vue/src/stores/live.test.ts`

**Interfaces:**
- Produces types `LiveRole`, `LiveConversation`, `LiveMessage`, `LiveRoleMemory`.
- Produces `historySliderToTurns(position: number): number` and `historyTurnsToSlider(turns: number): number` where 100 maps to 0/all.
- Produces store actions for role, conversation, message, memory and public preference management.

- [ ] **Step 1: Write failing nonlinear slider tests**

```typescript
it('accelerates toward the right and reserves the endpoint for all history', () => {
  expect(historySliderToTurns(0)).toBe(1)
  expect(historySliderToTurns(100)).toBe(0)
  expect(historySliderToTurns(75)).toBeGreaterThan(historySliderToTurns(50) * 1.5)
})
```

- [ ] **Step 2: Run the slider test and verify RED**

Run: `npm run test:unit -- src/live/history-context.test.ts`

Expected: module missing.

- [ ] **Step 3: Implement slider mapping and API types/functions**

Use a monotonic quadratic curve for positions 0 through 99 and reserve 100 for all history. Clamp and round results to 1 through 50.

- [ ] **Step 4: Write failing store tests**

Cover role-scoped conversation loading, per-role selected-conversation restoration, new call with `conversation_id: null`, continued call with selected conversation ID, final server message replacement, role config/public config separation, and settings lock while active.

- [ ] **Step 5: Run store tests and verify RED**

Run: `npm run test:unit -- src/stores/live.test.ts`

Expected: workspace actions or payload fields are missing.

- [ ] **Step 6: Implement store workspace state**

Use localStorage only for selected role/conversation IDs; all durable content comes from the backend. `startCall` creates a Live conversation only when there is no selected thread, then sends `{type:'session.start', role_id, conversation_id}`. Load persisted messages on selection and combine them with streaming state without duplicates.

- [ ] **Step 7: Rerun frontend unit tests and verify GREEN**

Run: `npm run test:unit`

Expected: all tests pass.

### Task 6: Role-aware Live interface and avatar signal core

**Files:**
- Create: `Agent-vue/src/components/live/LiveSidebar.vue`
- Create: `Agent-vue/src/components/live/LiveAvatarCore.vue`
- Create: `Agent-vue/src/components/live/LiveSettingsDeck.vue`
- Create: `Agent-vue/src/live/role-presentation.ts`
- Create: `Agent-vue/src/live/role-presentation.test.ts`
- Modify: `Agent-vue/src/views/LiveView.vue`

**Interfaces:**
- `LiveSidebar` emits role selection, new/select/rename/delete conversation, open-role-settings and open-public-settings actions.
- `LiveAvatarCore` consumes role, phase and muted state.
- `LiveSettingsDeck` edits either public call settings or role settings/memory without mixing payloads.

- [ ] **Step 1: Write failing role-presentation tests**

```typescript
it('uses two visible role initials when no avatar is set', () => {
  expect(roleInitials('黛黛')).toBe('黛黛')
  expect(roleInitials('Qwen Guide')).toBe('QG')
})

it('prefers a custom voice id over a selected built-in voice', () => {
  expect(resolveVoice('longanqian', 'clone-001')).toBe('clone-001')
})
```

- [ ] **Step 2: Run role-presentation tests and verify RED**

Run: `npm run test:unit -- src/live/role-presentation.test.ts`

Expected: helper module missing.

- [ ] **Step 3: Implement presentation helpers and focused components**

Keep the existing nocturnal broadcast-studio direction. Replace the central core fill with the current role avatar or initials, keep signal bars and orbit animations outside the image, and add accessible labels for role and call states.

- [ ] **Step 4: Recompose `LiveView.vue`**

The left rail becomes role and conversation navigation. The control deck exposes two sections:

- Call: model, nonlinear history injection length, `max_history_turns`.
- Role: name, avatar upload, system prompt, built-in voice buttons, custom voice ID, memory toggle, memory editor, save/clear/refresh.

Disable destructive navigation and critical settings during active calls. Keep responsive behavior at 920px and 680px breakpoints.

- [ ] **Step 5: Run frontend verification**

Run: `npm run test:unit; npm run type-check; npm run build-only`

Expected: all commands exit 0.

### Task 7: Full regression, real API and Chrome verification

**Files:**
- Modify only files required by a reproduced failure, with a failing regression test first.

**Interfaces:**
- Verifies all interfaces produced by Tasks 1 through 6.

- [ ] **Step 1: Run the complete backend suite**

Run: `.\venv\python.exe -m unittest discover -s AgentBI\tests -v`

Expected: 0 failures and 0 errors.

- [ ] **Step 2: Run the complete frontend suite and build**

Run: `npm run test:unit; npm run type-check; npm run build-only`

Expected: all commands exit 0.

- [ ] **Step 3: Run a credential-safe real upstream preparation smoke test**

Use `AgentBI/.env` without printing Key or Workspace ID. Open a Flash session, send `session.update`, inject one temporary system item and one user/assistant history pair, verify the upstream acknowledges every item, then close without microphone audio.

- [ ] **Step 4: Verify in Chrome without bypassing login**

With the user's authenticated local session, verify role creation, avatar core, role-scoped conversation lists, new/continued call behavior, both sliders, custom voice entry, memory toggle preservation, and conversation rename/delete. Do not activate microphone unless the user has already authorized the specific browser test.

- [ ] **Step 5: Review unstaged changes**

Run: `git diff --check; git status --short`

Expected: no whitespace errors and all implementation changes remain unstaged.
