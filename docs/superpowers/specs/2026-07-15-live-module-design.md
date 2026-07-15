# Live 实时语音模块设计规格

## 1. 目标与范围

在现有 AgentBI 工作台中，将当前聊天功能明确命名为 **Studio**，新增与其平级的 **Live** 模块。Live 一期提供基于阿里云百炼 Qwen-Audio Realtime 的低延迟实时语音对话，不接入 Studio 的助手能力、工具调用、子代理、记忆、RAG、上下文压缩或消息 DAG。

一期必须支持：

- Studio / Live 左上角模块切换。
- 开始通话、结束通话、麦克风静音与恢复。
- 用户语音的实时增量转写和最终转写。
- 模型回复的实时增量字幕和最终字幕。
- 模型 PCM 音频的流式播放。
- 用户说话时自动打断模型，并立即清空尚未播放的旧音频。
- `qwen-audio-3.0-realtime-flash` / `qwen-audio-3.0-realtime-plus` 选择。
- 阿里云系统音色选择。
- Live 独立系统提示词编辑。
- 按用户持久化 Live 配置。

一期不持久化通话转写，不恢复中断的实时会话，不支持声音复刻、工具调用、通话录音、摄像头、屏幕共享或手动 Push-to-talk。

## 2. 已考虑的接入方案

### 方案 A：浏览器直连阿里云

链路最短，但浏览器原生 `WebSocket` 无法设置官方连接要求的 `Authorization: Bearer ...` 请求头。把 API Key 放入 URL 或前端代码也会形成非标准协议和提供商耦合，因此不采用。

### 方案 B：FastAPI 透明代理全部阿里云 JSON 事件

实现简单，但前端需要理解阿里云 Base64 音频和全部原始事件，Live 页面会与单一提供商协议绑定，音频数据在本地链路仍有 Base64 膨胀。

### 方案 C：FastAPI 协议适配代理（采用）

浏览器与本地 FastAPI 使用项目内部稳定协议：二进制帧承载 PCM，JSON 帧承载控制、字幕和状态。FastAPI 负责连接阿里云、添加鉴权头、转换 Base64 PCM、筛选并规范化事件。该方案只增加一次本地 WebSocket 跳转，却能隔离提供商协议并为未来接入其他实时模型保留空间。

## 3. 模块边界

### 前端

- `AppModeSwitcher`：数据驱动的模块切换器，一期包含 Studio 和 Live，后续可直接增加 Playground。
- `LiveView`：Live 页面布局、状态展示、字幕时间线和配置面板。
- `live` Pinia Store：维护连接、通话、静音、字幕和错误状态，不复用 `chat` Store。
- `LiveSocketClient`：只负责项目内部 WebSocket 协议，不理解 Vue 组件。
- `MicrophoneCapture`：请求麦克风、采集音频、重采样为 16kHz 单声道 Int16 PCM，并以二进制帧发送。
- `PcmStreamPlayer`：接收 24kHz 单声道 Int16 PCM，维护播放队列并支持即时清空。
- AudioWorklet：承担音频重采样与连续播放，避免使用已废弃的 `ScriptProcessorNode`。

### 后端

- `api/live.py`：提供 Live 配置 REST 接口与 `/live/ws` WebSocket 入口。
- `services/live/qwen_audio_realtime.py`：负责阿里云 WebSocket 生命周期、事件转换和上游错误归一化。
- `services/live/protocol.py`：定义模型、音色、状态和内部事件名称，保持路由文件简洁。
- `SqliteChatRepository`：在同一 SQLite 文件中增加 Live 偏好表和读写方法；Live 配置继续通过仓储封装，不让 API 层直接执行 SQL。

Live 不是 Agent、子代理或 Tool，不进入现有能力注册表。

后端新增 `websockets>=15,<16` 作为阿里云上游客户端；前端新增 Vitest 作为纯 TypeScript 逻辑测试工具。除此之外，一期不引入实时音频或状态机框架。

## 4. 路由与页面结构

- 保留 Studio 当前 URL `/chat`，避免破坏现有会话恢复和外部入口。
- 新增受现有前端登录状态保护的 `/live`。
- `AppModeSwitcher` 同时出现在 Studio 左侧栏顶部和 Live 页面左上角。
- `App.vue` 继续作为路由出口，不在一期重构现有 Studio 页面结构。

Live 采用“夜间广播台”视觉方向：深色低反射背景、细密声学网格、单一电光青绿色强调色、大面积留白和清晰的通话状态光环。它与 Studio 的编辑工作台形成明显场景区分，但沿用项目现有字体尺度、圆角纪律和动效时长。配置面板不使用通用表单堆叠，而采用可收起的声场控制台布局。

页面主要区域：

1. 左上角 Studio / Live 切换器。
2. 顶部会话状态与 Flash / Plus 标识。
3. 中央声音状态舞台，显示连接中、聆听、思考、说话、已静音和错误。
4. 实时字幕时间线；用户与模型分别占据明确的视觉轨道。
5. 底部固定控制区：静音、开始/结束通话、设置。
6. 右侧设置抽屉：模型、音色、系统提示词。

## 5. 前后端内部协议

前端连接：

```text
ws://127.0.0.1:8000/live/ws?user_id=<current-user-id>
```

连接建立后的第一条前端 JSON 消息：

```json
{
  "type": "session.start",
  "model": "qwen-audio-3.0-realtime-flash",
  "voice": "longanqian",
  "instructions": "你是一位自然、简洁的实时语音助手。"
}
```

后续前端二进制帧均为 16kHz、16bit、单声道 PCM。静音时保持 WebSocket 连接，但停止发送二进制帧。

后端向前端发送的 JSON 事件：

- `session.ready`：阿里云 `session.updated` 已确认，允许开始发送音频。
- `state.listening`：服务端检测到用户开始说话。
- `state.thinking`：用户语音提交，等待模型首个响应。
- `state.speaking`：收到首个模型字幕或音频片段。
- `user.transcript.delta`：包含 `item_id`、`text`、`stash`。
- `user.transcript.final`：包含 `item_id`、`transcript`。
- `assistant.transcript.delta`：包含 `item_id`、`delta`。
- `assistant.transcript.final`：包含 `item_id`、`transcript`。
- `response.interrupted`：模型响应被用户打断。
- `response.completed`：本轮响应正常完成。
- `session.error`：包含稳定错误码、可展示消息和 `recoverable`。
- `session.closed`：上游或本地会话已结束。

后端向前端发送的二进制帧均为 24kHz、16bit、单声道模型 PCM。前端收到 `state.listening` 或 `response.interrupted` 时必须同步清空播放队列。

## 6. 阿里云协议映射

上游地址使用北京地域业务空间：

```text
wss://{WorkspaceId}.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime?model={ModelId}
```

后端从环境变量读取：

- `DASHSCOPE_API_KEY`
- `DASHSCOPE_WORKSPACE_ID`

首次 `session.update` 固定发送：

- `modalities: ["text", "audio"]`
- 用户选择的 `voice`
- 用户保存的 `instructions`
- `turn_detection.type: "smart_turn"`
- `max_history_turns: 20`

一期采用 `smart_turn`，利用语义轮次判断降低“嗯”“啊”等无意义声音造成的误打断。该模式和音色只能在首次发送音频前确定；模型位于连接 URL 中。因此模型或音色变更在通话中禁用，用户结束通话后才能修改。

关键映射：

- 前端二进制 PCM → `input_audio_buffer.append.audio` Base64。
- `conversation.item.input_audio_transcription.delta` → `user.transcript.delta`。
- `conversation.item.input_audio_transcription.completed` → `user.transcript.final`。
- `response.audio_transcript.delta` → `assistant.transcript.delta`。
- `response.audio_transcript.done` → `assistant.transcript.final`。
- `response.audio.delta` Base64 → 前端二进制 PCM。
- `input_audio_buffer.speech_started` → `state.listening`，同时触发前端清空播放队列。
- `input_audio_buffer.committed` → `state.thinking`。
- `response.done` 且 `status=cancelled` → `response.interrupted`。
- `response.done` 且 `status=completed` → `response.completed`。

## 7. 配置与持久化

新增 SQLite 表：

```sql
CREATE TABLE IF NOT EXISTS live_preferences (
    user_id TEXT PRIMARY KEY,
    model TEXT NOT NULL,
    voice TEXT NOT NULL,
    instructions TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

默认值：

- 模型：`qwen-audio-3.0-realtime-flash`
- 音色：`longanqian`
- 系统提示词：简洁、自然、适合口语输出且不使用 Markdown 的默认语音助手提示词。

允许的模型值仅为：

- `qwen-audio-3.0-realtime-flash`
- `qwen-audio-3.0-realtime-plus`

允许的系统音色值仅为：

- `longanqian`
- `longanlingxin`
- `longanlingxi`
- `longanxiaoxin`
- `longanlufeng`

REST 保存接口与 WebSocket 首帧都执行同一份模型、音色和提示词长度校验，防止持久化配置与实时协议产生分歧。

REST 接口：

- `GET /live/preferences?user_id=...`
- `PUT /live/preferences?user_id=...`

偏好以用户为边界，与 Studio 助手无关。设置保存成功后应用于下一次通话；正在进行的通话使用开始时的配置快照。

## 8. 状态机与交互规则

状态集合：

```text
idle → connecting → listening ↔ thinking ↔ speaking → ending → idle
                           ↘ error ↗
```

- “开始通话”由明确的用户点击触发，以满足浏览器麦克风权限和 `AudioContext` 自动播放限制。
- 只有收到 `session.ready` 后才发送麦克风帧。
- 静音只改变音频上行，不关闭上游连接，也不清空字幕。
- 结束通话立即停止采集、停止播放、清空缓冲并关闭本地及上游 WebSocket。
- 连接中、结束中按钮防重复触发。
- 页面离开、浏览器刷新和组件卸载都执行与结束通话相同的本地清理。
- 字幕按 `item_id` 更新同一条目，不为每个 delta 创建新气泡。
- 用户 `stash` 使用弱化样式附加在已确定文本后，最终事件到达后整体替换。

## 9. 错误与恢复

- 缺少 API Key 或 Workspace ID：在建立上游连接前返回不可恢复配置错误。
- 麦克风拒绝、无输入设备或 AudioWorklet 加载失败：保持 `idle/error`，不建立上游连接或立即关闭。
- 上游 `invalid_request_error`：展示参数错误，不自动重连。
- 上游 `server_error`、异常断线或本地网络失败：展示可恢复错误；一期提供“重新开始”按钮，不在同一次操作中无限自动重连。
- 后端日志保留阿里云事件类型和错误码，但不记录 API Key、完整音频或完整系统提示词。
- 任意错误都必须释放麦克风轨道、AudioContext、播放队列和两端 WebSocket。

## 10. 测试策略

后端继续采用现有 `unittest` 风格：

- 仓储测试：默认偏好、按用户隔离、保存后读取、非法枚举拒绝。
- 协议测试：阿里云字幕、音频、打断和完成事件映射为稳定内部事件。
- 代理测试：首次配置、二进制音频编码、上游错误归一化、关闭时资源释放。
- 路由测试：REST 路由与 WebSocket 路径已注册。

前端引入 Vitest，仅测试可独立运行的逻辑：

- Live Store 状态迁移和字幕按 `item_id` 合并。
- 静音时不发送音频帧。
- `state.listening` / `response.interrupted` 清空播放队列。
- 模型、音色在活动通话中不可变更。
- PCM 重采样和 Int16 边界转换使用确定性样本验证。

集成验收使用本机 Chrome：

1. 登录后可在 Studio / Live 间切换，Studio 当前会话不丢失。
2. 开始通话后状态依次进入连接和聆听，麦克风权限只在首次需要时请求。
3. 用户说话时实时出现稳定文本与暂存文本，结束后形成最终字幕。
4. 模型字幕和声音同时流式输出，不等待整轮完成。
5. 模型说话时用户插话，旧音频立即停止，界面出现被打断状态并继续接收新一轮。
6. 静音后模型不再收到用户音频，恢复后无需重连。
7. 结束通话后麦克风占用指示消失，刷新页面仍保留模型、音色和提示词配置。
8. Flash / Plus 和音色切换在下一次通话生效。

## 11. 一期完成标准

- Live 页面与 Studio 平级且视觉、状态、控制完整。
- 上述实时转写、字幕、播放、静音、打断和配置功能在真实阿里云模型上跑通。
- 后端单元测试、前端单元测试、Vue 类型检查和生产构建全部通过。
- Live 代码不导入 Agent、Tool、Memory、RAG 或聊天 DAG 模块。
- 不提交 Git，由项目所有者手动检查并提交变更。
