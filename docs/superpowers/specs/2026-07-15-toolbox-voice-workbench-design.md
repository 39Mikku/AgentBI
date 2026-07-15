# Toolbox 语音工作台设计

## 目标

在现有 Studio 中新增独立的 Toolbox 入口，并以“语音工作台”作为首个工具。工作台不调用大模型对话、不注册 Agent Tool，专注多供应商 TTS 日常生成和横向对比。

一期不实现声音复刻。用户在各供应商控制台完成复刻后，将已有音色 ID 添加到工作台。音色索引需要持久化；生成音频、波形和对比结果只在本次页面生命周期内存在，可当场播放或下载。

## 范围

### 供应商与模型

| 供应商 | 模型 | 音色范围 |
| --- | --- | --- |
| MiniMax | `speech-2.8-hd`、`speech-2.8-turbo` | 预置音色、用户添加的复刻 `voice_id` |
| 阿里云百炼 | `cosyvoice-v3.5-plus`、`cosyvoice-v3.5-flash` | 预置音色、用户添加的复刻 `voice_id` |
| 火山引擎 | `Doubao-Seed-TTS 2.0` | 预置音色 |
| 火山引擎 | `Doubao-Seed-ICL 2.0` | 用户添加的复刻 `speaker_id` |
| 小米 MiMo | `mimo-v2.5-tts` | 预置音色 |

一期明确不包含：声音复刻、声音设计、ASR、长期音频历史、生成任务数据库、Live 模块音色联动。

## 导航

- `Studio / Live` 继续只表示聊天与实时语音两种交互模式，Toolbox 不加入模式切换器。
- Studio 侧栏原“能力配置”入口替换为“工具箱”。
- 模型工作室与能力配置页现有顶部导航保留。
- 修正能力配置页顶部导航的高度、间距、对齐和选中状态，使其与模型工作室一致。
- Toolbox 首页展示工具卡片；点击“语音工作台”进入独立页面，并提供返回 Studio 和返回 Toolbox 的入口。

## 页面布局

桌面端采用左侧参数、右侧编辑区的两栏布局。

### 左侧参数控制台

- 单模型 / 对比模式开关。
- 供应商、模型、音色选择。
- 系统音色与“我的音色”分组。
- 添加、重命名、删除自定义音色。
- 公共参数和供应商专属高级参数。
- `.env` 配置状态，只显示已配置或缺失，不展示密钥内容。

### 右侧编辑与结果区

- 大尺寸文本编辑器、字符计数和生成按钮。
- 生成中状态与取消前端等待操作。
- 音频播放器、波形、模型、音色、耗时、格式和文件大小。
- 重试和下载按钮。
- 结果不写入数据库；离开页面时释放 Blob URL。

### 对比模式

- 所有推理轨道共用右侧文本。
- 左侧允许添加、移除和排序多个推理轨道。
- 每条轨道独立选择供应商、模型、音色和高级参数。
- 前端并发调用同一个单模型生成接口，不新增批量供应商协议。
- 每条轨道独立显示 loading、成功或失败，单个供应商失败不影响其他结果。
- 结果区按轨道并排展示，窄屏下改为纵向排列。

## 架构

采用“统一工作台 + 能力清单驱动的供应商适配器”。不把所有供应商压缩到最低公共参数，也不为每家供应商创建独立页面。

```text
AgentBI/src/services/toolbox/tts/
├── base.py
├── registry.py
├── minimax.py
├── bailian_cosyvoice.py
├── mimo.py
└── volcengine.py
```

统一领域对象：

- `TtsModelCapability`：模型、支持的音色类型、输出格式和参数定义。
- `TtsVoice`：供应商、显示名、外部音色 ID、音色类型和绑定模型。
- `TtsSynthesisRequest`：用户、文本、供应商、模型、音色、格式和扩展参数。
- `TtsSynthesisResult`：音频字节、MIME、格式、耗时和供应商元数据。

每个适配器实现能力声明、请求验证和语音合成。供应商差异保留在适配器内部，API 层不包含供应商条件分支。

## API

- `GET /toolbox/tts/capabilities`：返回可用供应商、模型、内置音色、参数定义和环境配置状态。
- `GET /toolbox/tts/voices?user_id=...`：读取用户添加的音色。
- `POST /toolbox/tts/voices`：添加音色。
- `PATCH /toolbox/tts/voices/{id}`：重命名或调整绑定模型。
- `DELETE /toolbox/tts/voices/{id}`：删除音色索引。
- `POST /toolbox/tts/synthesize`：单轨语音生成，成功时直接返回音频二进制。

音频响应通过响应头返回格式、供应商耗时和必要元数据。前端将响应转换为 Blob URL 用于播放和下载，因此后端不需要生成长期文件或清理任务。

## 音色持久化

在现有 SQLite 数据库新增 `toolbox_tts_voices` 表：

```text
id
user_id
provider
display_name
external_voice_id
voice_kind
bound_model
provider_metadata_json
created_at
updated_at
```

- 数据按登录用户的 `user_id` 隔离。
- 内置音色由能力清单提供，不重复写入数据库。
- MiniMax 和百炼保存复刻 `voice_id`；百炼必须保存绑定模型。
- 火山保存复刻 `speaker_id` 及 ICL 推理所需扩展字段。
- MiMo 一期不允许添加复刻音色。
- 数据库不保存音频正文、Blob、波形或生成记录。

## 环境变量

在 `AgentBI/.env.example` 和本地 `AgentBI/.env` 预留以下变量：

```dotenv
MINIMAX_API_KEY=
DASHSCOPE_API_KEY=
DASHSCOPE_WORKSPACE_ID=
MIMO_API_KEY=
VOLCENGINE_TTS_APP_ID=
VOLCENGINE_TTS_ACCESS_TOKEN=
VOLCENGINE_TTS_RESOURCE_ID=
VOLCENGINE_ICL_RESOURCE_ID=
```

现有百炼 Live 配置继续复用 `DASHSCOPE_API_KEY` 和 `DASHSCOPE_WORKSPACE_ID`。工作台不提供密钥编辑或数据库保存。

## 参数策略

- 公共层只统一文本、模型、音色和输出格式。
- 语速、音量、音调、情绪、语言增强、风格指令、上下文等能力由供应商能力清单动态展示。
- 单模型页面保留完整可用参数。
- 对比模式默认使用各模型推荐参数，用户可单独展开某条轨道的高级参数。
- 前端提交前执行通用校验，适配器再次执行供应商约束校验。

## 错误处理

- 缺少 `.env` 配置时禁用对应供应商并明确列出缺失变量。
- 供应商错误统一映射为配置错误、鉴权失败、限流、余额不足、请求无效和服务异常。
- 后端日志保留供应商 request ID，但不记录密钥和完整音频响应。
- 对比模式按轨道隔离错误；失败轨道可以单独重试。
- 收到不可识别的音频响应时不创建播放器，并显示供应商返回摘要。

## 测试

- 适配器契约测试：模型、音色类型、请求映射、响应解码和错误映射。
- API 测试：环境状态、音色 CRUD、用户隔离和二进制音频响应。
- Repository 测试：自定义音色持久化及模型绑定。
- 前端单元测试：单模型生成、对比并发、局部失败、Blob URL 释放和音色管理。
- 类型检查、生产构建和改动文件 lint。
- 配置密钥后，对四家供应商分别进行一次短文本真实调用，并验证播放与下载。

## 实施顺序

1. 补充 `.env` 与 `.env.example` 占位，等待用户填写测试凭据。
2. 实现 SQLite 音色目录与 API。
3. 建立 TTS 适配器协议和能力清单。
4. 逐家接入 MiniMax、百炼、MiMo、火山。
5. 实现 Toolbox 导航、首页和语音工作台单模型模式。
6. 实现对比模式和结果卡片。
7. 修复能力配置页顶部导航样式。
8. 自动化回归与真实供应商测试。
