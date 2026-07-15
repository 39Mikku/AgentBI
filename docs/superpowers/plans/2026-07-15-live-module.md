# Live Realtime Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready Live page beside Studio with persistent Qwen-Audio Realtime settings, full-duplex browser audio, streaming transcripts, streaming playback, mute, and interruption.

**Architecture:** Vue talks to one local FastAPI WebSocket using normalized JSON control events and binary PCM frames. FastAPI owns the Alibaba Cloud credential, translates the internal protocol to Qwen-Audio Realtime JSON/Base64 events, and stores user preferences in the existing SQLite repository.

**Tech Stack:** Vue 3, Pinia, TypeScript, Web Audio/AudioWorklet, Vitest, FastAPI, Python `websockets`, SQLite, `unittest`.

## Global Constraints

- Keep Studio at `/chat`; add Live at `/live`.
- Work in the current checkout on `codex/sqlite-chat-storage`; do not create another worktree.
- Do not commit or stage Git changes; the project owner commits manually.
- Live must not import Agent, Tool, Memory, RAG, or chat DAG modules.
- Accept only `qwen-audio-3.0-realtime-flash` and `qwen-audio-3.0-realtime-plus`.
- Accept only `longanqian`, `longanlingxin`, `longanlingxi`, `longanxiaoxin`, and `longanlufeng`.
- Use `smart_turn`, input PCM 16kHz/16bit/mono, output PCM 24kHz/16bit/mono.
- Write a failing test before every production behavior; configuration-only edits are exempt.

---

### Task 1: Environment and Live preference persistence

**Files:**
- Modify: `AgentBI/.env`
- Modify: `AgentBI/requirements.txt`
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Create: `AgentBI/tests/test_live_preferences.py`

**Interfaces:**
- Produces: `get_live_preferences(user_id: str) -> dict[str, Any]`
- Produces: `save_live_preferences(user_id: str, payload: dict[str, Any]) -> dict[str, Any]`

- [ ] **Step 1: Add empty environment variables without changing existing values**

```dotenv
DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
```

- [ ] **Step 2: Write failing repository tests**

```python
def test_live_preferences_have_stable_defaults_and_are_isolated_by_user(self):
    self.assertEqual(self.repo.get_live_preferences("alice")["model"], "qwen-audio-3.0-realtime-flash")
    self.repo.save_live_preferences("alice", {"model": "qwen-audio-3.0-realtime-plus"})
    self.assertEqual(self.repo.get_live_preferences("alice")["model"], "qwen-audio-3.0-realtime-plus")
    self.assertEqual(self.repo.get_live_preferences("bob")["model"], "qwen-audio-3.0-realtime-flash")
```

- [ ] **Step 3: Run the repository test and confirm it fails because the methods do not exist**

Run: `python -m unittest AgentBI.tests.test_live_preferences -v`

- [ ] **Step 4: Add `live_preferences` schema and repository methods**

```python
DEFAULT_LIVE_PREFERENCES = {
    "model": "qwen-audio-3.0-realtime-flash",
    "voice": "longanqian",
    "instructions": "你是一位自然、简洁的实时语音助手。请使用适合口语朗读的纯文本回答。",
}
```

- [ ] **Step 5: Add `websockets>=15,<16` and rerun the repository tests**

Run: `python -m unittest AgentBI.tests.test_live_preferences -v`
Expected: all tests pass.

### Task 2: Live schemas and REST routes

**Files:**
- Create: `AgentBI/src/api/live.py`
- Modify: `AgentBI/main.py`
- Modify: `AgentBI/tests/test_live_preferences.py`
- Modify: `AgentBI/tests/test_chat_routes.py`

**Interfaces:**
- Produces: `GET /live/preferences?user_id=...`
- Produces: `PUT /live/preferences?user_id=...`
- Produces: `WS /live/ws?user_id=...`

- [ ] **Step 1: Write failing schema and route-registration tests**

```python
def test_live_preferences_reject_unknown_models_and_voices(self):
    with self.assertRaises(ValidationError):
        LivePreferencesUpdate(model="unknown", voice="unknown", instructions="hello")

def test_live_routes_are_registered(self):
    paths = {route.path for route in app.routes}
    self.assertIn("/live/preferences", paths)
    self.assertIn("/live/ws", paths)
```

- [ ] **Step 2: Run tests and confirm missing imports/routes fail**

Run: `python -m unittest AgentBI.tests.test_live_preferences AgentBI.tests.test_chat_routes -v`

- [ ] **Step 3: Implement Pydantic models and REST handlers**

```python
class LivePreferencesUpdate(BaseModel):
    model: Literal["qwen-audio-3.0-realtime-flash", "qwen-audio-3.0-realtime-plus"]
    voice: Literal["longanqian", "longanlingxin", "longanlingxi", "longanxiaoxin", "longanlufeng"]
    instructions: str = Field(min_length=1, max_length=12000)
```

- [ ] **Step 4: Register `live_router` in `main.py` and rerun tests**

Run: `python -m unittest AgentBI.tests.test_live_preferences AgentBI.tests.test_chat_routes -v`
Expected: all tests pass.

### Task 3: Alibaba Cloud protocol adapter and proxy

**Files:**
- Create: `AgentBI/src/services/live/__init__.py`
- Create: `AgentBI/src/services/live/protocol.py`
- Create: `AgentBI/src/services/live/qwen_audio_realtime.py`
- Modify: `AgentBI/src/api/live.py`
- Create: `AgentBI/tests/test_live_protocol.py`
- Create: `AgentBI/tests/test_live_session.py`

**Interfaces:**
- Produces: `map_upstream_event(event: dict[str, Any]) -> list[LiveEvent | LiveAudio]`
- Produces: `QwenAudioRealtimeSession.run(frontend: WebSocket, config: LiveSessionConfig) -> None`
- Consumes: frontend binary 16kHz PCM and upstream Qwen-Audio JSON events.

- [ ] **Step 1: Write failing event mapping tests**

```python
def test_transcript_and_interrupt_events_map_to_internal_protocol(self):
    self.assertEqual(map_upstream_event({"type": "response.audio_transcript.delta", "item_id": "a", "delta": "你好"})[0].type, "assistant.transcript.delta")
    self.assertEqual(map_upstream_event({"type": "response.done", "response": {"status": "cancelled"}})[0].type, "response.interrupted")
```

- [ ] **Step 2: Run protocol tests and confirm the module is missing**

Run: `python -m unittest AgentBI.tests.test_live_protocol -v`

- [ ] **Step 3: Implement typed protocol mapping, Base64 helpers, and stable error mapping**

```python
@dataclass(frozen=True)
class LiveEvent:
    type: str
    payload: dict[str, Any]

@dataclass(frozen=True)
class LiveAudio:
    pcm: bytes
```

- [ ] **Step 4: Write failing session tests with injected upstream connector**

```python
async def test_session_sends_first_update_and_forwards_binary_audio(self):
    session = QwenAudioRealtimeSession(api_key="key", workspace_id="ws", connector=fake_connector)
    await session.run(frontend, config)
    self.assertEqual(upstream.sent_json[0]["type"], "session.update")
    self.assertEqual(upstream.sent_json[1]["type"], "input_audio_buffer.append")
```

- [ ] **Step 5: Run session tests and confirm missing session behavior fails**

Run: `python -m unittest AgentBI.tests.test_live_session -v`

- [ ] **Step 6: Implement bidirectional tasks, cleanup, and `/live/ws` wiring**

```python
async with websockets.connect(url, additional_headers={"Authorization": f"Bearer {api_key}"}) as upstream:
    await asyncio.gather(forward_frontend_audio(), forward_upstream_events())
```

- [ ] **Step 7: Run all Live backend tests**

Run: `python -m unittest AgentBI.tests.test_live_preferences AgentBI.tests.test_live_protocol AgentBI.tests.test_live_session AgentBI.tests.test_chat_routes -v`
Expected: all tests pass.

### Task 4: Frontend Live protocol and state model

**Files:**
- Modify: `Agent-vue/package.json`
- Create: `Agent-vue/src/api/live-types.ts`
- Create: `Agent-vue/src/api/live.ts`
- Create: `Agent-vue/src/live/live-state.ts`
- Create: `Agent-vue/src/live/live-state.test.ts`
- Create: `Agent-vue/src/stores/live.ts`

**Interfaces:**
- Produces: `mergeLiveEvent(state: LiveState, event: LiveServerEvent) -> LiveState`
- Produces: Pinia actions `loadPreferences`, `savePreferences`, `startCall`, `endCall`, `toggleMute`.

- [ ] **Step 1: Add Vitest and write failing state tests**

```typescript
it('merges transcript deltas by item id and clears playback on interruption', () => {
  const state = createLiveState()
  mergeLiveEvent(state, { type: 'assistant.transcript.delta', item_id: 'a', delta: '你' })
  mergeLiveEvent(state, { type: 'assistant.transcript.delta', item_id: 'a', delta: '好' })
  expect(state.transcripts[0].text).toBe('你好')
  expect(mergeLiveEvent(state, { type: 'response.interrupted' }).clearPlayback).toBe(true)
})
```

- [ ] **Step 2: Run Vitest and confirm missing module failure**

Run: `npm run test:unit -- src/live/live-state.test.ts`

- [ ] **Step 3: Implement types, pure reducer, REST API and store orchestration**

```typescript
export type LivePhase = 'idle' | 'connecting' | 'listening' | 'thinking' | 'speaking' | 'ending' | 'error'
```

- [ ] **Step 4: Rerun unit tests**

Run: `npm run test:unit -- src/live/live-state.test.ts`
Expected: all tests pass.

### Task 5: Browser audio pipeline

**Files:**
- Create: `Agent-vue/src/live/pcm.ts`
- Create: `Agent-vue/src/live/pcm.test.ts`
- Create: `Agent-vue/src/live/MicrophoneCapture.ts`
- Create: `Agent-vue/src/live/PcmStreamPlayer.ts`
- Create: `Agent-vue/public/worklets/microphone-processor.js`
- Create: `Agent-vue/public/worklets/pcm-player-processor.js`

**Interfaces:**
- Produces: `resampleFloat32(input, sourceRate, targetRate): Float32Array`
- Produces: `floatToInt16(input): Int16Array`
- Produces: `MicrophoneCapture.start(onPcm)` / `stop()` / `setMuted()`.
- Produces: `PcmStreamPlayer.start()` / `enqueue()` / `clear()` / `stop()`.

- [ ] **Step 1: Write failing deterministic PCM conversion tests**

```typescript
it('converts and clamps float samples to signed 16 bit PCM', () => {
  expect([...floatToInt16(new Float32Array([-2, -1, 0, 1, 2]))]).toEqual([-32768, -32768, 0, 32767, 32767])
})
```

- [ ] **Step 2: Run PCM tests and confirm missing functions fail**

Run: `npm run test:unit -- src/live/pcm.test.ts`

- [ ] **Step 3: Implement PCM utilities, AudioWorklets, capture and playback wrappers**

```typescript
export function floatToInt16(input: Float32Array): Int16Array {
  return Int16Array.from(input, (sample) => sample < 0 ? Math.max(-1, sample) * 32768 : Math.min(1, sample) * 32767)
}
```

- [ ] **Step 4: Run PCM and state tests**

Run: `npm run test:unit`
Expected: all tests pass.

### Task 6: Module switcher and Live interface

**Files:**
- Create: `Agent-vue/src/components/AppModeSwitcher.vue`
- Create: `Agent-vue/src/views/LiveView.vue`
- Modify: `Agent-vue/src/views/ChatView.vue`
- Modify: `Agent-vue/src/router/index.ts`

**Interfaces:**
- Consumes: `useLiveStore()` and `useAuthStore()`.
- Produces: authenticated `/live` page and Studio/Live navigation.

- [ ] **Step 1: Add `/live` route and reusable module switcher**

```typescript
{ path: '/live', name: 'live', component: () => import('@/views/LiveView.vue'), meta: { title: 'Live · AgentBI', requiresAuth: true } }
```

- [ ] **Step 2: Implement the nocturnal broadcast-studio Live layout**

```vue
<AppModeSwitcher active="live" />
<main class="live-stage" :data-phase="live.phase">
  <section class="signal-orb" aria-live="polite">{{ live.statusLabel }}</section>
  <section class="transcript-rail"><!-- keyed transcript rows --></section>
</main>
```

- [ ] **Step 3: Wire call, mute, model, voice and prompt controls with disabled states**

- [ ] **Step 4: Run frontend unit tests, type-check and build**

Run: `npm run test:unit && npm run type-check && npm run build-only`
Expected: all commands exit 0.

### Task 7: Full verification and real API smoke test

**Files:**
- Modify only files required to fix a reproduced failure, with a failing regression test first.

- [ ] **Step 1: Run the complete backend suite**

Run: `python -m unittest discover -s AgentBI/tests -v`
Expected: 0 failures and 0 errors.

- [ ] **Step 2: Run the complete frontend suite**

Run: `npm run test:unit && npm run type-check && npm run build-only`
Expected: all commands exit 0.

- [ ] **Step 3: Start backend and frontend after the user fills both DashScope variables**

Run: `python -m AgentBI.main` and `npm run dev -- --host 127.0.0.1`.

- [ ] **Step 4: Verify in Chrome**

Confirm Studio state survives navigation, Live preferences persist, user/model subtitles stream, audio plays before completion, mute suppresses outbound frames, interruption clears queued audio, and end call releases the microphone.

- [ ] **Step 5: Review `git diff` and leave all changes unstaged for the user**

Run: `git diff --check && git status --short`
Expected: no whitespace errors; all Live changes remain unstaged.
