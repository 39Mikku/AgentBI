# 能力全局配置与 Tavily 搜索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为每个用户提供跨助手共享、按能力完全隔离的配置，并接入由主模型直接调用的 Tavily 网页搜索工具。

**Architecture:** SQLite 使用 `(user_id, capability_id)` 作为唯一键保存 JSON 配置；统一注册表容纳直接工具与子代理，并为每项能力定义独立校验模型和 UI 元数据。助手只保存 `capability_ids`；Tavily 结果作为 tool message 回到主模型循环，子代理仍执行各自的专项循环。

**Tech Stack:** FastAPI、Pydantic、SQLite、Vue 3、TypeScript、CSS。

## Global Constraints

- 使用 `capability_settings`，不在配置表中加入 `assistant_id`。
- 不同 `capability_id` 的配置不得互相读取或覆盖。
- 未保存配置时使用子代理注册时的默认值。
- 默认助手和自定义助手挂载同一能力时读取同一份用户配置。
- `tool.web_search` 不启动子代理模型，调用后必须回到主模型继续生成。
- Git 提交由用户手动完成，本计划不执行暂存或提交。

---

### Task 1: 配置持久化与 API

**Files:**
- Create: `AgentBI/src/schemas/subagent_settings_schema.py`
- Create: `AgentBI/src/api/subagent_settings.py`
- Modify: `AgentBI/src/repositories/sqlite_chat_repository.py`
- Modify: `AgentBI/main.py`
- Test: `AgentBI/tests/test_subagent_settings.py`

- [ ] 先写测试，验证默认值、按能力隔离、按用户隔离和非法参数拒绝。
- [ ] 运行目标测试并确认因接口尚不存在而失败。
- [ ] 新增 `subagent_settings` 表和 GET/PUT API，使测试通过。

### Task 2: 运行时参数接入

**Files:**
- Modify: `AgentBI/src/agents/assistant_registry.py`
- Modify: `AgentBI/src/agents/chat_agent.py`
- Modify: `AgentBI/src/agents/music_agent.py`
- Modify: `AgentBI/src/agents/bilibili_agent.py`
- Modify: `AgentBI/src/services/netease_music_client.py`
- Modify: `AgentBI/src/services/bilibili_client.py`
- Modify: `AgentBI/src/tools/music_tools.py`
- Modify: `AgentBI/src/tools/bilibili_tools.py`
- Test: `AgentBI/tests/test_music_agent.py`
- Test: `AgentBI/tests/test_bilibili_agent.py`
- Test: `AgentBI/tests/test_bilibili_client.py`

- [ ] 先写测试，验证音乐数量、Bilibili 数量互不影响，以及指定 UP 主稿件检索。
- [ ] 运行目标测试并确认失败原因是参数尚未接入。
- [ ] 委派时读取 `user_id + capability_id` 配置并注入目标子代理。
- [ ] 为 Bilibili 增加 `search_creator_videos`，使用 CLI 的 `user-videos` 候选并按标题/简介本地筛选。

### Task 3: 子代理配置页与侧栏滚动条

**Files:**
- Create: `Agent-vue/src/api/subagent-settings.ts`
- Create: `Agent-vue/src/views/SubagentSettingsView.vue`
- Modify: `Agent-vue/src/api/chat-types.ts`
- Modify: `Agent-vue/src/router/index.ts`
- Modify: `Agent-vue/src/views/ChatView.vue`
- Test: `Agent-vue/tests/subagent-settings.test.ts`

- [ ] 先写 API 映射测试并确认失败。
- [ ] 新增 `/settings/subagents`，每张卡片只提交自己的 `capability_id` 和配置。
- [ ] 在工作台侧栏增加入口。
- [ ] 为 `.conversation-list` 定义窄型深色滚动条及 Firefox 等价样式。

### Task 4: 验证

- [ ] 运行 `python -m unittest discover -s AgentBI/tests -v`。
- [ ] 运行前端 Node 测试、`npm run type-check` 和 `npm run build-only`。
- [ ] 检查 `git diff --check` 和工作区差异，不暂存、不提交。
