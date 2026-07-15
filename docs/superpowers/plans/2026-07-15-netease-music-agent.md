# 网易云音乐子代理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 AgentBI 内无感启动 NeteaseCloudMusicApiEnhanced，并通过可挂载 MusicAgent 将搜索、日推和点歌结果作为可播放卡片推入当前聊天时间线。

**Architecture:** FastAPI lifespan 持有隐藏的 Node 子进程，Python `NeteaseMusicClient` 只访问 `127.0.0.1` 内部 API。主代理只暴露 `delegate_music`，MusicAgent 使用受限音乐工具产生通用 `card` 事件；前端按 `card.kind` 渲染并延迟获取音频地址。

**Tech Stack:** FastAPI, asyncio subprocess, httpx, OpenAI-compatible tool calls, SQLite JSON timeline, Vue 3, Pinia, HTMLAudioElement, NeteaseCloudMusicApiEnhanced.

## Global Constraints

- 用户只启动 AgentBI 后端，不手动启动 Node 服务。
- Node 只监听 `127.0.0.1:3300`，Windows 不弹新终端。
- Cookie 只从 `AgentBI/.env` 读取，不进入 SQLite、日志、SSE 或前端。
- 播放 URL 不持久化，点击播放时即时获取。
- Node 或网易云调用失败不得终止普通聊天流。
- 主代理不得直接访问音乐原子工具。
- 默认助手挂载 `agent.music`，自定义助手按配置挂载。
- 不暂存或提交 Git，由用户手动提交。

---

### Task 1: 内置 Node 服务与生命周期管理

**Files:**
- Create: `AgentBI/vendor/netease-music-api/package.json`
- Create: `AgentBI/vendor/netease-music-api/app.cjs`
- Create: `AgentBI/src/services/music_api_process.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_music_api_process.py`

**Interfaces:**
- Produces: `MusicApiProcessManager.start()`, `stop()`, `ensure_running()`, `available`, `base_url`.
- Stores manager at `app.state.music_api_process`.

- [ ] Write lifecycle tests for health polling, availability, one restart attempt, and cleanup using a fake process/health probe.
- [ ] Run `.\venv\python.exe -m unittest AgentBI.tests.test_music_api_process` and confirm the module is missing.
- [ ] Implement `MusicApiProcessManager(enabled, port, startup_timeout, command=None)` with async `start`, `ensure_running`, and `stop`.
- [ ] Launch `node app.cjs` directly with `asyncio.create_subprocess_exec`; use hidden/no-window flags on Windows, bounded health polling, sanitized log forwarding, and terminate/kill cleanup.
- [ ] Create the Node wrapper, pin Enhanced API in `package.json`, and generate `package-lock.json` with `npm install` in the vendor directory.
- [ ] Load `AgentBI/.env` in FastAPI lifespan, start the manager without failing FastAPI, and always stop it before closing SQLite.
- [ ] Run focused lifecycle and route tests.

---

### Task 2: 稳定音乐客户端、Schema 与播放端点

**Files:**
- Create: `AgentBI/src/schemas/music_schema.py`
- Create: `AgentBI/src/services/netease_music_client.py`
- Create: `AgentBI/src/api/music.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_netease_music_client.py`
- Modify: `AgentBI/tests/test_chat_routes.py`

**Interfaces:**
- Consumes: `MusicApiProcessManager.base_url`, `ensure_running()`.
- Produces: `MusicTrack`, `MusicCard`, `NeteaseMusicClient.search_tracks()`, `daily_recommendations()`, `resolve_track()`, `resolve_playback_url()`.

- [ ] Write failing tests for search/daily response variants, multiple artists, covers, duration, unavailable tracks, expired Cookie, and Cookie redaction.
- [ ] Run the focused test and confirm missing modules.
- [ ] Implement `MusicTrack` with `id`, `name`, `artists`, `album`, `cover_url`, `duration_ms`, `available`, and `unavailable_reason`.
- [ ] Implement the async client with injected `httpx.AsyncClient`, fixed timeouts, normalized errors, maximum three search candidates and ten recommendations.
- [ ] Add `GET /music/status` and `GET /music/tracks/{track_id}/stream`; the latter resolves a fresh URL and returns `RedirectResponse`.
- [ ] Register the router and verify paths plus client tests.

---

### Task 3: 通用 card 时间线事件

**Files:**
- Modify: `AgentBI/src/services/chat_service.py`
- Modify: `AgentBI/src/api/chat.py`
- Modify: `AgentBI/tests/test_chat_core.py`
- Modify: `Agent-vue/src/api/chat-types.ts`
- Modify: `Agent-vue/src/stores/chat.ts`
- Create: `Agent-vue/src/utils/card-events.ts`
- Create: `Agent-vue/tests/card-events.test.ts`

**Interfaces:**
- Produces backend event: `{"type": "card", "kind": str, "payload": dict}`.
- Produces frontend timeline entry with `type: 'card'`, `kind`, and `payload`.

- [ ] Write failing backend/frontend tests proving card position is preserved and unknown card kinds do not throw.
- [ ] Run focused tests and confirm failure.
- [ ] Make `append_timeline_event` append cards without merging; forward `card` over SSE and persist only in `timeline`.
- [ ] Add TypeScript card payload contracts and structured card consumption in the Pinia chat store.
- [ ] Run focused tests and `npm run type-check --prefix Agent-vue`.

---

### Task 4: MusicAgent、工具隔离与主代理委派

**Files:**
- Create: `AgentBI/src/tools/music_tools.py`
- Create: `AgentBI/src/agents/music_agent.py`
- Modify: `AgentBI/src/agents/assistant_registry.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/api/chat.py`
- Test: `AgentBI/tests/test_music_agent.py`
- Modify: `AgentBI/tests/test_chat_agent.py`

**Interfaces:**
- Consumes: `NeteaseMusicClient` and card event contract.
- Produces: capability `agent.music`, main tool `delegate_music`, and subagent tools `search_tracks`, `daily_recommendations`, `resolve_track`.

- [ ] Write failing tests for default capability registration, conditional `delegate_music`, exact MusicAgent tool whitelist, and Cookie-free tool output.
- [ ] Run focused tests and confirm failure.
- [ ] Implement async music tool wrappers and MusicAgent's streamed tool loop, following EmailAgent while injecting only `NeteaseMusicClient`.
- [ ] Emit normalized card events for successful search/daily/resolve; convert all upstream failures into tool results.
- [ ] Register `agent.music` and delegate from ChatAgent only when mounted, preserving timeline order.
- [ ] Run focused and full backend tests.

---

### Task 5: 音乐卡片与共享播放器

**Files:**
- Create: `Agent-vue/src/api/music.ts`
- Create: `Agent-vue/src/stores/player.ts`
- Create: `Agent-vue/src/components/cards/MusicTrackCard.vue`
- Create: `Agent-vue/src/components/cards/MusicTrackListCard.vue`
- Create: `Agent-vue/src/components/cards/TimelineCard.vue`
- Modify: `Agent-vue/src/views/ChatView.vue`
- Modify: `Agent-vue/src/views/AssistantsView.vue`
- Create: `Agent-vue/src/utils/music-player.ts`
- Create: `Agent-vue/tests/music-player.test.ts`

**Interfaces:**
- Consumes: `music.track`, `music.track-list`, `/api/music/tracks/{id}/stream`.
- Produces: one shared audio state with `play(track)`, `pause()`, and `toggle(track)`.

- [ ] Write a failing fake-audio test for track switching, toggle, error state, and lazy URL construction.
- [ ] Run the focused test and confirm failure.
- [ ] Implement API, pure player controller, and Pinia store without storing final upstream URLs.
- [ ] Build compact editorial single-track/list cards with cover, metadata, active equalizer, disabled reason, and safe unknown-card fallback.
- [ ] Render cards at their exact ChatView timeline positions.
- [ ] Add the `agent.music` checkbox beside email in the assistant editor.
- [ ] Run focused tests, Vue type checking, and production build.

---

### Task 6: Live integration, documentation, and final verification

**Files:**
- Modify: `AgentBI/requirements.txt`
- Create: `AgentBI/.env.example`
- Modify: `docs/AgentBI_开发总览.md`
- Modify: `docs/子代理模块开发说明.md`

**Interfaces:**
- Consumes all previous tasks.
- Produces reproducible setup and verified live music flow.

- [ ] Document automatic process lifecycle, all `NCM_*` variables, Cookie refresh, and the generic card extension point; `.env.example` keeps Cookie empty.
- [ ] Install the locked Node dependency and start AgentBI normally; confirm no visible Node terminal and `/music/status` ready.
- [ ] With the user's local Cookie, smoke-test search, daily recommendations, and one stream redirect without printing Cookie or playback URL.
- [ ] Run full verification:

```powershell
.\venv\python.exe -m compileall -q AgentBI
.\venv\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"
npm run build --prefix Agent-vue
git diff --check
```

Expected: zero failures and exit code 0.
