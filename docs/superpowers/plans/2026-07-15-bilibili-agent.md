# Bilibili 视频子代理 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加可挂载的 Bilibili 搜索子代理，并将视频卡片接入聊天时间线和官方内嵌播放器弹窗。

**Architecture:** FastAPI 进程内通过 `bilibili-api-python` 获取公开搜索和详情数据，项目客户端统一标准化字段。子代理产生现有通用 `card` 事件；Vue 根据 `card.kind` 渲染视频卡片并用 BV 号构造官方播放器 iframe。

**Tech Stack:** FastAPI, httpx, OpenAI-compatible tool calls, SQLite JSON timeline, Vue 3, Pinia, Node tests.

## Global Constraints

- 不启动 `bili.exe` 子进程，不自动读取浏览器 Cookie。
- 一期只使用公开搜索、详情和官方 iframe 播放器。
- 卡片不保存 Cookie 或临时播放直链。
- 默认助手挂载 `agent.bilibili`，自定义助手按配置挂载。
- 所有生产行为先有失败测试，再写最小实现。
- 不执行 Git 暂存或提交，由用户手动提交。

---

### Task 1: Bilibili 数据边界和客户端

**Files:**
- Create: `AgentBI/src/schemas/bilibili_schema.py`
- Create: `AgentBI/src/services/bilibili_client.py`
- Create: `AgentBI/tests/test_bilibili_client.py`
- Modify: `AgentBI/requirements.txt`

**Interfaces:**
- Produces: `BilibiliVideo`, `BilibiliClient.search_videos(query, limit=3)`, `BilibiliClient.get_video(bvid)`.

- [ ] 写失败测试，固定搜索字段标准化、详情字段标准化、数量限制、空查询和上游异常。
- [ ] 运行 `venv\Scripts\python.exe -m unittest AgentBI.tests.test_bilibili_client -v`，确认因模块不存在失败。
- [ ] 实现 schema 和可注入异步搜索/详情函数的客户端；生产默认调用 `bilibili_api.search` 与 `bilibili_api.video`。
- [ ] 使用项目已有 `httpx` 调用公开搜索与详情接口，避免为两项公开能力引入 Pillow 等完整 CLI 依赖。
- [ ] 重跑测试，确认通过。

### Task 2: 工具、子代理和统一依赖注册

**Files:**
- Create: `AgentBI/src/tools/bilibili_tools.py`
- Create: `AgentBI/src/agents/bilibili_agent.py`
- Create: `AgentBI/tests/test_bilibili_agent.py`
- Modify: `AgentBI/src/agents/assistant_registry.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/api/chat.py`
- Modify: `AgentBI/tests/test_chat_agent.py`

**Interfaces:**
- Produces: capability `agent.bilibili`, delegate `delegate_bilibili`, tools `search_videos` and `get_video_detail`.
- Produces: `create_subagent(delegate_name, dependencies={...})` dependency lookup.

- [ ] 写失败测试，固定能力注册、条件挂载、工具白名单、空结果无卡片和卡片中不含临时播放地址。
- [ ] 运行聚焦测试并确认预期失败。
- [ ] 实现工具结果与 BilibiliAgent 流式工具循环。
- [ ] 将注册器依赖选择改成按名字查询，并在聊天路由注入 `BilibiliClient`。
- [ ] 重跑聚焦测试和后端全量测试。

### Task 3: 视频卡片和官方播放器弹窗

**Files:**
- Create: `Agent-vue/src/utils/bilibili-player.ts`
- Create: `Agent-vue/tests/bilibili-player.test.ts`
- Create: `Agent-vue/src/components/cards/BilibiliVideoCard.vue`
- Create: `Agent-vue/src/components/cards/BilibiliVideoListCard.vue`
- Create: `Agent-vue/src/components/BilibiliPlayerModal.vue`
- Modify: `Agent-vue/src/components/cards/TimelineCard.vue`
- Modify: `Agent-vue/src/views/ChatView.vue`

**Interfaces:**
- Consumes: `bilibili.video`, `bilibili.video-list` cards.
- Produces: `buildBilibiliPlayerUrl(bvid, page=1)` and a single chat-scoped player modal.

- [ ] 写失败测试，固定合法 BV 号的播放器 URL、官方链接、分页和非法 BV 号拒绝行为。
- [ ] 运行 `node --test Agent-vue/tests/bilibili-player.test.ts` 并确认模块不存在失败。
- [ ] 实现纯播放器 URL 工具。
- [ ] 实现编辑排版的视频列表/单视频卡片，通过事件打开播放器。
- [ ] 在 `ChatView` 持有单一弹窗状态，并从任意时间线卡片切换当前视频。
- [ ] 运行前端测试、类型检查和生产构建。

### Task 4: 文档和最终验证

**Files:**
- Modify: `docs/AgentBI_开发总览.md`
- Modify: `docs/子代理模块开发说明.md`

- [ ] 记录 `agent.bilibili`、数据流、官方播放器限制和扩展点。
- [ ] 运行公开搜索 smoke test，确认真实上游仍可返回结果但不把结果写入仓库。
- [ ] 运行 `venv\Scripts\python.exe -m unittest discover -s AgentBI\tests -p "test_*.py"`。
- [ ] 运行 `npm run build --prefix Agent-vue`。
- [ ] 运行 `git diff --check` 并检查只包含本功能相关文件。
