# Bilibili 视频子代理一期设计

## 目标

为 AgentBI 增加可挂载的 Bilibili 子代理。主助手把视频搜索、视频详情和点播请求委派给子代理；子代理将结果作为通用时间线卡片返回。用户点击卡片后，在聊天页内打开浮动窗口，使用哔哩哔哩官方内嵌播放器播放。

## 一期范围

- 公开关键词搜索，默认最多返回 3 个视频。
- 根据 BV 号获取视频详情。
- `bilibili.video-list` 与 `bilibili.video` 两类通用卡片。
- 官方播放器弹窗，支持关闭、切换视频和“在 B 站打开”兜底。
- 默认助手自动挂载 `agent.bilibili`，自定义助手可以选择挂载。
- 搜索和详情失败时返回稳定文本，不中断主聊天流。

一期不包含登录、收藏、点赞、投币、评论、历史记录、字幕总结、自建 DASH 播放器或视频代理。

## 架构

后端复用 `bilibili-cli` 的公开接口边界与字段规范，但通过项目已有的 `httpx` 直接请求公开搜索和详情接口，不在请求期间启动 `bili.exe` 子进程，也不引入其与搜索无关的 Pillow 等完整依赖。项目内的 `BilibiliClient` 负责隔离上游字段，`BilibiliAgent` 只暴露搜索和详情工具。通用 `card` SSE、SQLite 时间线和历史恢复沿用现有实现。

前端卡片只保存稳定元数据：BV 号、标题、作者、封面、时长、播放量和官方页面地址。播放器 URL 由前端根据 BV 号生成：

```text
https://player.bilibili.com/player.html?bvid={bvid}&page=1&high_quality=1&danmaku=0&autoplay=0
```

播放器 iframe 使用最小权限和明确的 `referrerpolicy`；卡片始终保留官方页面链接作为兜底。

## 模块

```text
AgentBI/src/schemas/bilibili_schema.py
AgentBI/src/services/bilibili_client.py
AgentBI/src/tools/bilibili_tools.py
AgentBI/src/agents/bilibili_agent.py

Agent-vue/src/utils/bilibili-player.ts
Agent-vue/src/components/cards/BilibiliVideoCard.vue
Agent-vue/src/components/cards/BilibiliVideoListCard.vue
Agent-vue/src/components/BilibiliPlayerModal.vue
```

现有子代理注册器改为按依赖名从字典取依赖，避免继续增加二选一分支。

## 数据结构

```json
{
  "bvid": "BV1xx411c7mD",
  "title": "视频标题",
  "author": "UP 主",
  "cover_url": "https://...",
  "duration_seconds": 120,
  "play_count": 10000,
  "published_at": 0,
  "description": "",
  "url": "https://www.bilibili.com/video/BV1xx411c7mD"
}
```

## 错误处理与测试

- 非法 BV 号在 schema/客户端边界拒绝。
- 上游异常转换成 `BilibiliClientError`，工具只向模型返回简短中文错误。
- 空搜索结果不生成空卡片。
- iframe URL 只接受通过正则校验的 BV 号，避免把任意字符串拼进播放器地址。
- 后端单元测试使用假上游函数，不访问真实 B 站；另做一次手动公开搜索 smoke test。
- 前端纯函数测试覆盖播放器 URL、官方链接和非法 BV 号。

## 验收标准

- 默认助手和已挂载该能力的自定义助手可以搜索 Bilibili 视频。
- 搜索结果按真实时间线显示为卡片，刷新会话后仍存在。
- 点击任一视频卡片，在聊天页内打开官方播放器；关闭弹窗不影响会话。
- 未挂载能力的助手不会收到 Bilibili 委派工具。
- 后端测试、前端测试、类型检查和生产构建通过。
